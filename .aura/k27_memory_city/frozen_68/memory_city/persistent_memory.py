"""SQLite revision bindings for the recovered K27Path / FrameAddress runtime.

Explicit local storage only; no providers, background sync, or inference calls.
Each public mutation is one transaction. Exact revisions are immutable. Current
objects carry state and a frame-qualified address; addresses need not be unique.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
import sqlite3
from coordinate_bridge import checked_address, checked_path, path_key, address_record, nonempty
from world_atlas import FrameAddress

class MemoryConflict(ValueError): pass
class StaleMemory(ValueError): pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

class MemoryStore:
    def __init__(self, filename):
        self.db = sqlite3.connect(str(filename), timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 2):
            self.db.close()
            raise ValueError('unsupported memory schema version')
        if version == 0:
            names = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if names:
                self.db.close()
                raise ValueError('refusing to initialize an unrelated database')
            self.db.executescript('''
            BEGIN IMMEDIATE;
            CREATE TABLE frames(frame_id TEXT PRIMARY KEY, generation TEXT NOT NULL);
            CREATE TABLE revisions(revision_id TEXT PRIMARY KEY, object_id TEXT NOT NULL,
                envelope TEXT NOT NULL, payload_sha256 TEXT NOT NULL);
            CREATE TABLE objects(object_id TEXT PRIMARY KEY, current_rev TEXT NOT NULL REFERENCES revisions,
                state TEXT NOT NULL CHECK(state IN ('fresh','stale','retracted')),
                frame_id TEXT NOT NULL REFERENCES frames, frame_generation TEXT NOT NULL, path TEXT NOT NULL,
                epoch INTEGER NOT NULL CHECK(epoch > 0));
            CREATE TABLE dependencies(revision_id TEXT NOT NULL REFERENCES revisions,
                source_object TEXT NOT NULL, source_rev TEXT NOT NULL REFERENCES revisions,
                PRIMARY KEY(revision_id, source_object));
            CREATE INDEX dependency_reverse ON dependencies(source_object,revision_id);
            CREATE INDEX city_prefix ON objects(frame_id,frame_generation,path,state);
            PRAGMA user_version=2;
            COMMIT;
            ''')
        expected = {
            'frames': ('frame_id','generation'),
            'revisions': ('revision_id','object_id','envelope','payload_sha256'),
            'objects': ('object_id','current_rev','state','frame_id','frame_generation','path','epoch'),
            'dependencies': ('revision_id','source_object','source_rev'),
        }
        for table, columns in expected.items():
            actual = tuple(row['name'] for row in self.db.execute(f'PRAGMA table_info({table})'))
            if actual != columns:
                self.db.close()
                raise ValueError(f'incompatible memory schema table: {table}')
    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    @contextmanager
    def _write(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def _invalidate(self, roots):
        pending, seen, affected = list(roots), set(roots), set()
        while pending:
            parent = pending.pop()
            rows = self.db.execute('''SELECT o.object_id, o.state FROM dependencies d
                JOIN objects o ON o.current_rev=d.revision_id WHERE d.source_object=?''', (parent,)).fetchall()
            for row in rows:
                key = row['object_id']
                if key in seen: continue
                seen.add(key); pending.append(key)
                if row['state'] == 'fresh':
                    self.db.execute("UPDATE objects SET state='stale',epoch=epoch+1 WHERE object_id=?", (key,))
                    affected.add(key)
        return affected

    def register_frame(self, frame_id, generation, *, expected_generation=None):
        nonempty(frame_id,'frame_id'); nonempty(generation,'generation')
        with self._write():
            old = self.db.execute('SELECT generation FROM frames WHERE frame_id=?',(frame_id,)).fetchone()
            actual = old[0] if old else None
            if actual != expected_generation:
                raise MemoryConflict('frame generation changed; supply the observed generation')
            if actual == generation: return []
            self.db.execute('INSERT INTO frames VALUES(?,?) ON CONFLICT(frame_id) DO UPDATE SET generation=excluded.generation',(frame_id,generation))
            roots = {r[0] for r in self.db.execute("SELECT object_id FROM objects WHERE frame_id=? AND state='fresh'",(frame_id,))}
            self.db.execute("UPDATE objects SET state='stale',epoch=epoch+1 WHERE frame_id=? AND state='fresh'",(frame_id,))
            return sorted(roots | self._invalidate(roots))

    def _require_current(self, object_id, revision):
        row = self.db.execute('''SELECT o.current_rev,o.state,o.frame_generation,f.generation
            FROM objects o JOIN frames f USING(frame_id) WHERE object_id=?''',(object_id,)).fetchone()
        if not row or row[0] != revision or row[1] != 'fresh' or row[2] != row[3]:
            raise StaleMemory(f'input is missing, changed, retired, or stale: {object_id}')

    def _check_cycle(self, object_id, dependencies):
        pending, seen = list(dependencies), set()
        while pending:
            parent = pending.pop()
            if parent == object_id: raise MemoryConflict('current object dependency cycle')
            if parent in seen: continue
            seen.add(parent)
            pending.extend(r[0] for r in self.db.execute('''SELECT d.source_object FROM objects o
                JOIN dependencies d ON d.revision_id=o.current_rev WHERE o.object_id=?''',(parent,)))

    def publish(self, object_id, payload, address, *, source_url, source_version,
                expected_revision=None, expected_epoch=None, dependencies=None):
        nonempty(object_id,'object_id'); nonempty(source_url,'source_url'); nonempty(source_version,'source_version')
        checked_address(address)
        if address.canonical_ref != object_id: raise ValueError('address must bind the exact object identity')
        if dependencies is None: dependencies = {}
        if not isinstance(dependencies, dict): raise ValueError('dependencies must map object IDs to exact revisions')
        for key, rev in dependencies.items(): nonempty(key,'dependency object'); nonempty(rev,'dependency revision')
        payload_text = canonical(payload)
        envelope = {'object_id':object_id, 'payload':json.loads(payload_text), 'address':address_record(address),
                    'source_url':source_url, 'source_version':source_version, 'dependencies':dict(sorted(dependencies.items()))}
        encoded = canonical(envelope)
        revision = sha256(encoded.encode()).hexdigest()
        with self._write():
            frame = self.db.execute('SELECT generation FROM frames WHERE frame_id=?',(address.frame_id,)).fetchone()
            if not frame or frame[0] != address.frame_generation: raise StaleMemory('address frame generation is not current')
            prior = self.db.execute('SELECT current_rev,epoch FROM objects WHERE object_id=?',(object_id,)).fetchone()
            if (prior[0] if prior else None) != expected_revision: raise MemoryConflict('object revision changed; reload before publishing')
            if prior:
                if type(expected_epoch) is not int or prior['epoch'] != expected_epoch:
                    raise MemoryConflict('object lifecycle epoch changed; reload before publishing')
            elif expected_epoch is not None:
                raise MemoryConflict('new objects require expected_epoch=None')
            for key, rev in dependencies.items(): self._require_current(key,rev)
            self._check_cycle(object_id, dependencies)
            self.db.execute('INSERT OR IGNORE INTO revisions VALUES(?,?,?,?)',
                            (revision,object_id,encoded,sha256(payload_text.encode()).hexdigest()))
            for key, rev in dependencies.items():
                self.db.execute('INSERT OR IGNORE INTO dependencies VALUES(?,?,?)',(revision,key,rev))
            epoch = prior['epoch'] + 1 if prior else 1
            self.db.execute('''INSERT INTO objects VALUES(?,?,'fresh',?,?,?,?)
                ON CONFLICT(object_id) DO UPDATE SET current_rev=excluded.current_rev,state='fresh',
                frame_id=excluded.frame_id,frame_generation=excluded.frame_generation,path=excluded.path,epoch=excluded.epoch''',
                (object_id,revision,address.frame_id,address.frame_generation,path_key(address.path),epoch))
            affected = self._invalidate([object_id]) if prior and prior[0] != revision else set()
            return {'object_id':object_id,'revision_id':revision,'epoch':epoch,'invalidated':sorted(affected)}

    def get(self, object_id, *, allow_stale=False):
        row = self.db.execute('''SELECT r.envelope,r.revision_id,r.payload_sha256,o.state,
            o.frame_generation,f.generation,o.epoch FROM objects o JOIN revisions r ON r.revision_id=o.current_rev
            JOIN frames f USING(frame_id) WHERE o.object_id=?''',(object_id,)).fetchone()
        if row is None: return None
        state = row['state'] if row['frame_generation'] == row['generation'] else ('retracted' if row['state']=='retracted' else 'stale')
        if state != 'fresh' and not allow_stale: raise StaleMemory(f'{object_id}: {state}')
        return {**json.loads(row['envelope']), 'revision_id':row['revision_id'], 'payload_sha256':row['payload_sha256'],
                'state':state,'epoch':row['epoch'],'currentness_scope':'local registry consistency only'}

    def history(self, object_id, revision_id):
        row = self.db.execute('SELECT envelope,payload_sha256 FROM revisions WHERE object_id=? AND revision_id=?',(object_id,revision_id)).fetchone()
        return None if row is None else {**json.loads(row[0]),'revision_id':revision_id,'payload_sha256':row[1],'state':'historical; currentness not asserted'}

    def retract(self, object_id, *, expected_revision, expected_epoch):
        with self._write():
            row = self.db.execute('SELECT current_rev,epoch FROM objects WHERE object_id=?',(object_id,)).fetchone()
            if not row or row[0] != expected_revision or type(expected_epoch) is not int or row['epoch'] != expected_epoch:
                raise MemoryConflict('retraction revision or lifecycle epoch changed')
            self.db.execute("UPDATE objects SET state='retracted',epoch=epoch+1 WHERE object_id=?",(object_id,))
            return sorted(self._invalidate([object_id]))

    def under(self, frame_id, generation, prefix=()):
        nonempty(frame_id,'frame_id'); nonempty(generation,'generation'); checked_path(prefix)
        key = path_key(prefix)
        # Current frame and revision data are resolved together by this one read statement.
        rows = self.db.execute('''SELECT r.envelope,r.revision_id,r.payload_sha256,o.epoch FROM objects o
            JOIN frames f USING(frame_id) JOIN revisions r ON r.revision_id=o.current_rev
            WHERE o.frame_id=? AND o.frame_generation=? AND f.generation=?
            AND o.path>=? AND o.path<? AND o.state='fresh' ORDER BY o.path,o.object_id''',
            (frame_id,generation,generation,key,key+'\uffff')).fetchall()
        return [{**json.loads(r[0]),'revision_id':r[1],'payload_sha256':r[2],'state':'fresh','epoch':r[3],
                 'currentness_scope':'local registry consistency only'} for r in rows]

    def project(self, object_id, atlas, destination_frame):
        # Pin source and destination registry state in the same SQLite snapshot.
        self.db.execute('BEGIN')
        try:
            result = self._project_snapshot(object_id,atlas,destination_frame)
            self.db.execute('COMMIT')
            return result
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def _project_snapshot(self, object_id, atlas, destination_frame):
        record = self.get(object_id)
        if record is None: return None
        a = record['address']
        addr = FrameAddress(a['frame_id'],a['frame_generation'],tuple(a['path']),object_id)
        if addr.frame_id != destination_frame:
            transform = atlas.transforms.get((addr.frame_id,destination_frame))
            if transform is not None and (tuple(sorted(transform.axis_perm)) != (0,1,2)
                or any(type(v) is not int for v in transform.axis_perm)
                or len(transform.invert) != 3 or any(type(v) is not bool for v in transform.invert)):
                raise ValueError('invalid axis permutation or inversion flags')
        projected = atlas.project(addr,destination_frame)
        checked_address(projected)
        frame = self.db.execute('SELECT generation FROM frames WHERE frame_id=?',(destination_frame,)).fetchone()
        if not frame or frame[0] != projected.frame_generation: raise StaleMemory('projected frame is not current in persistent registry')
        return projected
