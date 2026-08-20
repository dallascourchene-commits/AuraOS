"""Aura Project006 Resident V2 staged reference IPC core.
Trusted local control plane only: AF_UNIX, bounded framed canonical JSON, no provider endpoints/secrets.
"""
from __future__ import annotations
import hashlib, json, re, socket, struct
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

PROTOCOL_VERSION='AURA_RESIDENT_IPC_V2'
RECEIPT_VERSION='AURA_RESIDENT_RECEIPT_V2'
MAX_FRAME_BYTES=256*1024
MAX_DEPTH=12
MAX_CONTAINER_ITEMS=2048
MAX_STRING_BYTES=128*1024
HEADER=struct.Struct('!I')
NORMAL_TYPES=frozenset({'HEALTH','STATUS','WORK_SUBMIT','WORK_STATUS','WORK_CANCEL'})
ADMIN_TYPES=frozenset({'ADMIN_DRAIN','ADMIN_RECONCILE'})
ALLOWED_TYPES=NORMAL_TYPES|ADMIN_TYPES
TOP_LEVEL_FIELDS=frozenset({'protocol_version','message_type','request_id','generation','issued_at_ms','expires_at_ms','authority_ref','currentness_ref','payload','extensions'})
REQUIRED_TOP_LEVEL_FIELDS=frozenset({'protocol_version','message_type','request_id','generation','issued_at_ms','expires_at_ms','authority_ref','currentness_ref','payload'})
REQUEST_ID_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$')
REF_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,255}$')
SENSITIVE_KEY_FRAGMENTS=('token','password','passwd','secret','api_key','apikey','authorization','cookie','private_key','credential')
NETWORK_KEY_FRAGMENTS=('provider_url','provider_host','network_endpoint','http_url','https_url','ip_address','dns_name')

class IPCError(ValueError):
    def __init__(self, reason): super().__init__(reason); self.reason=reason

def canonical_json_bytes(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha256_hex(data): return hashlib.sha256(data).hexdigest()
def _pairs_no_duplicates(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise IPCError('DUPLICATE_JSON_KEY')
        d[k]=v
    return d

def _walk_limits(value,depth=0):
    if depth>MAX_DEPTH: raise IPCError('STRUCTURE_TOO_DEEP')
    if isinstance(value,str):
        if len(value.encode())>MAX_STRING_BYTES: raise IPCError('STRING_TOO_LARGE')
        return
    if value is None or isinstance(value,(bool,int)): return
    if isinstance(value,float): raise IPCError('FLOAT_NOT_ALLOWED')
    if isinstance(value,list):
        if len(value)>MAX_CONTAINER_ITEMS: raise IPCError('CONTAINER_TOO_LARGE')
        for x in value: _walk_limits(x,depth+1)
        return
    if isinstance(value,dict):
        if len(value)>MAX_CONTAINER_ITEMS: raise IPCError('CONTAINER_TOO_LARGE')
        for k,v in value.items():
            if not isinstance(k,str): raise IPCError('NON_STRING_KEY')
            kl=k.lower()
            if any(x in kl for x in SENSITIVE_KEY_FRAGMENTS): raise IPCError('SENSITIVE_FIELD_FORBIDDEN')
            if any(x in kl for x in NETWORK_KEY_FRAGMENTS): raise IPCError('NETWORK_ENDPOINT_FIELD_FORBIDDEN')
            _walk_limits(v,depth+1)
        return
    raise IPCError('UNSUPPORTED_JSON_TYPE')

def decode_frame_payload(payload):
    if not payload or len(payload)>MAX_FRAME_BYTES: raise IPCError('FRAME_SIZE_INVALID')
    try: text=payload.decode('utf-8')
    except UnicodeDecodeError as e: raise IPCError('INVALID_UTF8') from e
    try:
        obj=json.loads(text,object_pairs_hook=_pairs_no_duplicates,parse_constant=lambda _x: (_ for _ in ()).throw(IPCError('NONFINITE_NUMBER')))
    except IPCError: raise
    except Exception as e: raise IPCError('MALFORMED_JSON') from e
    if not isinstance(obj,dict): raise IPCError('TOP_LEVEL_NOT_OBJECT')
    _walk_limits(obj); return obj

def encode_frame(obj):
    body=canonical_json_bytes(obj)
    if not body or len(body)>MAX_FRAME_BYTES: raise IPCError('FRAME_SIZE_INVALID')
    return HEADER.pack(len(body))+body

def recv_exact(sock,n):
    out=bytearray()
    while len(out)<n:
        chunk=sock.recv(n-len(out))
        if not chunk: raise IPCError('TRUNCATED_FRAME')
        out.extend(chunk)
    return bytes(out)
def recv_frame(sock):
    length=HEADER.unpack(recv_exact(sock,HEADER.size))[0]
    if length<2 or length>MAX_FRAME_BYTES: raise IPCError('FRAME_SIZE_INVALID')
    return decode_frame_payload(recv_exact(sock,length))
def send_frame(sock,obj): sock.sendall(encode_frame(obj))

def _validate_ref(name,value):
    if not isinstance(value,str) or not REF_RE.fullmatch(value): raise IPCError('INVALID_'+name.upper())
    return value

def _require_exact_payload(payload,required,optional=()):
    req,opt=set(required),set(optional); keys=set(payload)
    if req-keys: raise IPCError('PAYLOAD_MISSING_REQUIRED_FIELD')
    if keys-(req|opt): raise IPCError('PAYLOAD_UNKNOWN_FIELD')

def _validate_payload(mt,p):
    if mt in {'HEALTH','STATUS','ADMIN_RECONCILE'}: _require_exact_payload(p,()); return
    if mt=='WORK_SUBMIT':
        _require_exact_payload(p,('capsule_id','capsule_digest','route_ref','deadline_ms'),('source_refs','dependency_ids','body_ref'))
        _validate_ref('capsule_id',p['capsule_id']); _validate_ref('route_ref',p['route_ref'])
        if not isinstance(p['capsule_digest'],str) or not re.fullmatch(r'[0-9a-f]{64}',p['capsule_digest']): raise IPCError('INVALID_CAPSULE_DIGEST')
        if not isinstance(p['deadline_ms'],int) or isinstance(p['deadline_ms'],bool): raise IPCError('INVALID_DEADLINE')
        for lf in ('source_refs','dependency_ids'):
            if lf in p:
                if not isinstance(p[lf],list) or len(p[lf])>256: raise IPCError('INVALID_'+lf.upper())
                for v in p[lf]: _validate_ref(lf[:-1],v)
        if 'body_ref' in p: _validate_ref('body_ref',p['body_ref'])
        return
    if mt in {'WORK_STATUS','WORK_CANCEL'}:
        _require_exact_payload(p,('capsule_id',),('reason_code',) if mt=='WORK_CANCEL' else ())
        _validate_ref('capsule_id',p['capsule_id'])
        if 'reason_code' in p: _validate_ref('reason_code',p['reason_code'])
        return
    if mt=='ADMIN_DRAIN': _require_exact_payload(p,('reason_code',)); _validate_ref('reason_code',p['reason_code']); return
    raise IPCError('UNKNOWN_MESSAGE_TYPE')

def validate_envelope(obj):
    _walk_limits(obj)
    keys=set(obj)
    if REQUIRED_TOP_LEVEL_FIELDS-keys: raise IPCError('MISSING_REQUIRED_FIELD')
    if keys-TOP_LEVEL_FIELDS: raise IPCError('UNKNOWN_TOP_LEVEL_FIELD')
    if obj['protocol_version']!=PROTOCOL_VERSION: raise IPCError('UNSUPPORTED_PROTOCOL_VERSION')
    if obj['message_type'] not in ALLOWED_TYPES: raise IPCError('UNKNOWN_MESSAGE_TYPE')
    if not isinstance(obj['request_id'],str) or not REQUEST_ID_RE.fullmatch(obj['request_id']): raise IPCError('INVALID_REQUEST_ID')
    _validate_ref('generation',obj['generation']); _validate_ref('authority_ref',obj['authority_ref']); _validate_ref('currentness_ref',obj['currentness_ref'])
    for f in ('issued_at_ms','expires_at_ms'):
        if not isinstance(obj[f],int) or isinstance(obj[f],bool): raise IPCError('INVALID_'+f.upper())
    if obj['expires_at_ms']<obj['issued_at_ms']: raise IPCError('INVALID_EXPIRY_WINDOW')
    if not isinstance(obj['payload'],dict): raise IPCError('PAYLOAD_NOT_OBJECT')
    if 'extensions' in obj and not isinstance(obj['extensions'],dict): raise IPCError('EXTENSIONS_NOT_OBJECT')
    _validate_payload(obj['message_type'],obj['payload']); return dict(obj)

@dataclass
class ResidentState:
    generation:str
    currentness_ref:str
    owner_uid:int
    state_epoch:int=1
    draining:bool=False
    work_states:Dict[str,str]=field(default_factory=dict)
    seen:Dict[str,Tuple[str,Dict[str,Any]]]=field(default_factory=dict)
    def snapshot(self):
        return {'generation':self.generation,'currentness_ref':self.currentness_ref,'state_epoch':self.state_epoch,'draining':self.draining,'accepted_work_count':sum(1 for x in self.work_states.values() if x=='ACCEPTED'),'tracked_work_count':len(self.work_states)}

def _decision_receipt(req,state,decision,reason,result=None):
    core={'receipt_version':RECEIPT_VERSION,'request_id':req.get('request_id','UNBOUND'),'request_digest':sha256_hex(canonical_json_bytes(req)),'decision':decision,'reason_code':reason,'state_snapshot':state.snapshot(),'result':dict(result or {})}
    core['decision_digest']=sha256_hex(canonical_json_bytes(core)); return core

def process_request(raw,state,now_ms,peer_uid):
    req=validate_envelope(raw); dig=sha256_hex(canonical_json_bytes(req)); rid=req['request_id']
    prior=state.seen.get(rid)
    if prior:
        if prior[0]==dig: return dict(prior[1])
        return _decision_receipt(req,state,'REJECT','REQUEST_ID_COLLISION')
    def finish(decision,reason,result=None):
        receipt=_decision_receipt(req,state,decision,reason,result); state.seen[rid]=(dig,receipt); return receipt
    if req['generation']!=state.generation: return finish('REJECT','STALE_OR_FOREIGN_GENERATION')
    if req['currentness_ref']!=state.currentness_ref: return finish('REJECT','CURRENTNESS_MISMATCH')
    if now_ms>req['expires_at_ms']: return finish('REJECT','REQUEST_EXPIRED')
    if req['message_type'] in ADMIN_TYPES and peer_uid!=state.owner_uid: return finish('REJECT','ADMIN_PEER_NOT_OWNER')
    mt,p=req['message_type'],req['payload']
    if mt=='HEALTH': return finish('ACCEPT','HEALTH_OK',{'healthy':True})
    if mt=='STATUS': return finish('ACCEPT','STATUS_OK',state.snapshot())
    if mt=='WORK_SUBMIT':
        if state.draining: return finish('REJECT','RESIDENT_DRAINING')
        if p['deadline_ms']<now_ms: return finish('REJECT','WORK_DEADLINE_EXPIRED')
        cid=p['capsule_id']
        if cid in state.work_states: return finish('REJECT','CAPSULE_ALREADY_TRACKED')
        state.work_states[cid]='ACCEPTED'; state.state_epoch+=1
        return finish('ACCEPT','WORK_ACCEPTED',{'capsule_id':cid,'route_ref':p['route_ref']})
    if mt=='WORK_STATUS':
        cid=p['capsule_id']; return finish('ACCEPT','WORK_STATUS_OK',{'capsule_id':cid,'work_state':state.work_states.get(cid,'UNKNOWN')})
    if mt=='WORK_CANCEL':
        cid=p['capsule_id']
        if cid not in state.work_states: return finish('REJECT','CAPSULE_UNKNOWN')
        state.work_states[cid]='CANCELLED'; state.state_epoch+=1; return finish('ACCEPT','WORK_CANCELLED',{'capsule_id':cid})
    if mt=='ADMIN_DRAIN': state.draining=True; state.state_epoch+=1; return finish('ACCEPT','DRAIN_ENABLED')
    if mt=='ADMIN_RECONCILE': state.state_epoch+=1; return finish('ACCEPT','RECONCILE_MARKED')
    return finish('REJECT','UNKNOWN_MESSAGE_TYPE')

def make_unix_listener(path,backlog=32):
    if not hasattr(socket,'AF_UNIX'): raise RuntimeError('AF_UNIX unavailable')
    s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    try: s.bind(path); s.listen(backlog); return s
    except Exception: s.close(); raise

def get_peer_uid(sock):
    """Linux/WSL peer identity witness for a connected AF_UNIX stream socket."""
    if not hasattr(socket, 'SO_PEERCRED'):
        raise IPCError('PEER_CREDENTIALS_UNAVAILABLE')
    raw=sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    _pid, uid, _gid=struct.unpack('3i', raw)
    return uid
