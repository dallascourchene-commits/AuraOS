import ast, os, socket, struct, tempfile, unittest
from pathlib import Path
import resident_v2_ipc as r
NOW=1_800_000_000_000

def req(mt='HEALTH',rid='REQ-00000001',payload=None,**overrides):
    x={'protocol_version':r.PROTOCOL_VERSION,'message_type':mt,'request_id':rid,'generation':'gen-current','issued_at_ms':NOW-100,'expires_at_ms':NOW+1000,'authority_ref':'authority:local-owner','currentness_ref':'currentness:1','payload':payload or {}}
    x.update(overrides); return x

class T(unittest.TestCase):
    def state(self): return r.ResidentState('gen-current','currentness:1',owner_uid=1000)
    def test_01_health(self): self.assertEqual(r.process_request(req(),self.state(),NOW,1000)['reason_code'],'HEALTH_OK')
    def test_02_truncated(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            a.sendall(struct.pack('!I',10)+b'{}'); a.shutdown(socket.SHUT_WR)
            with self.assertRaisesRegex(r.IPCError,'TRUNCATED_FRAME'): r.recv_frame(b)
        finally: a.close(); b.close()
    def test_03_oversize(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            a.sendall(struct.pack('!I',r.MAX_FRAME_BYTES+1))
            with self.assertRaisesRegex(r.IPCError,'FRAME_SIZE_INVALID'): r.recv_frame(b)
        finally: a.close(); b.close()
    def test_04_version(self):
        with self.assertRaisesRegex(r.IPCError,'UNSUPPORTED_PROTOCOL_VERSION'): r.validate_envelope(req(protocol_version='V999'))
    def test_05_unknown_message(self):
        with self.assertRaisesRegex(r.IPCError,'UNKNOWN_MESSAGE_TYPE'): r.validate_envelope(req(message_type='PROVIDER_HTTP_CALL'))
    def test_06_idempotent(self):
        s=self.state(); q=req(); a=r.process_request(q,s,NOW,1000); b=r.process_request(q,s,NOW+1,1000); self.assertEqual(a,b)
    def test_07_request_id_collision(self):
        s=self.state(); r.process_request(req(),s,NOW,1000); self.assertEqual(r.process_request(req(mt='STATUS'),s,NOW,1000)['reason_code'],'REQUEST_ID_COLLISION')
    def test_08_stale_generation(self): self.assertEqual(r.process_request(req(generation='gen-old'),self.state(),NOW,1000)['reason_code'],'STALE_OR_FOREIGN_GENERATION')
    def test_09_currentness(self): self.assertEqual(r.process_request(req(currentness_ref='currentness:old'),self.state(),NOW,1000)['reason_code'],'CURRENTNESS_MISMATCH')
    def test_10_expired(self): self.assertEqual(r.process_request(req(expires_at_ms=NOW-1),self.state(),NOW,1000)['reason_code'],'REQUEST_EXPIRED')
    def test_11_admin_nonowner(self): self.assertEqual(r.process_request(req('ADMIN_RECONCILE'),self.state(),NOW,2000)['reason_code'],'ADMIN_PEER_NOT_OWNER')
    def test_12_secret(self):
        q=req(); q['payload']={'api_key':'x'}
        with self.assertRaisesRegex(r.IPCError,'SENSITIVE_FIELD_FORBIDDEN'): r.validate_envelope(q)
    def test_13_provider_endpoint(self):
        q=req(); q['payload']={'provider_url':'https://example.invalid'}
        with self.assertRaisesRegex(r.IPCError,'NETWORK_ENDPOINT_FIELD_FORBIDDEN'): r.validate_envelope(q)
    def test_14_stale_socket_not_unlinked(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,'resident.sock'); Path(p).write_text('occupied')
            with self.assertRaises(OSError): r.make_unix_listener(p)
            self.assertTrue(Path(p).exists())
    def test_15_partial_read(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            f=r.encode_frame(req())
            for byte in f: a.send(bytes([byte]))
            self.assertEqual(r.recv_frame(b)['request_id'],'REQ-00000001')
        finally: a.close(); b.close()
    def test_16_submit_status(self):
        s=self.state(); q=req('WORK_SUBMIT','REQ-SUBMIT01',{'capsule_id':'capsule:001','capsule_digest':'a'*64,'route_ref':'route:sidecar-default','deadline_ms':NOW+5000,'source_refs':['source:abc']})
        self.assertEqual(r.process_request(q,s,NOW,1000)['reason_code'],'WORK_ACCEPTED')
        st=r.process_request(req('WORK_STATUS','REQ-STATUS01',{'capsule_id':'capsule:001'}),s,NOW,1000)
        self.assertEqual(st['result']['work_state'],'ACCEPTED')
    def test_17_work_deadline(self):
        q=req('WORK_SUBMIT','REQ-SUBMIT02',{'capsule_id':'capsule:002','capsule_digest':'b'*64,'route_ref':'route:sidecar-default','deadline_ms':NOW-1})
        self.assertEqual(r.process_request(q,self.state(),NOW,1000)['reason_code'],'WORK_DEADLINE_EXPIRED')
    def test_18_unknown_top(self):
        q=req(); q['provider']='deepseek'
        with self.assertRaisesRegex(r.IPCError,'UNKNOWN_TOP_LEVEL_FIELD'): r.validate_envelope(q)
    def test_19_duplicate_json_key(self):
        with self.assertRaisesRegex(r.IPCError,'DUPLICATE_JSON_KEY'): r.decode_frame_payload(b'{"a":1,"a":2}')
    def test_20_no_ip_http_surface(self):
        src=Path(r.__file__).read_text(); tree=ast.parse(src); imports=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import): imports|={x.name.split('.')[0] for x in n.names}
            elif isinstance(n,ast.ImportFrom) and n.module: imports.add(n.module.split('.')[0])
        self.assertFalse(imports & {'requests','urllib','http','aiohttp','httpx'}); self.assertNotIn('AF_INET',src); self.assertNotIn('AF_INET6',src)
    def test_21_digest_reproducible(self):
        q=req(); self.assertEqual(r.process_request(q,self.state(),NOW,1000)['decision_digest'],r.process_request(q,self.state(),NOW,1000)['decision_digest'])
    def test_22_peer_credentials(self):
        a,b=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
        try: self.assertEqual(r.get_peer_uid(b), os.getuid())
        finally: a.close(); b.close()

if __name__=='__main__': unittest.main(verbosity=2)
