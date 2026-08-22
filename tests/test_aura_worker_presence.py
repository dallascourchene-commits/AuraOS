import hashlib
import pytest
from aura_worker_presence import *

def d(s): return hashlib.sha256(s.encode()).hexdigest()
def joined(w="w1",t=1000):
    return join_runtime_worker(worker_instance_id=w,session_id="s-"+w,model="deepseek-chat",provider="deepseek",
      device_ref="laptop",runtime_ref="resident",evidence_independence_group="eig-"+w,lease_generation=1,
      fencing_token_digest=d("f-"+w),received_at_ms=t,capability_profile_digest=d("cap-"+w),
      authority_ceiling_digest=d("auth"),currentness_digest=d("cur"))
def hb(p,seq=1,state=RuntimePresenceState.WORKING,claim="c1",reported=1):
    return HeartbeatV1(p.worker_instance_id,p.session_id,p.lease_generation,p.fencing_token_digest,seq,state,
      "WO-C",claim,"X","W1",d("cur"),d("auth"),reported)
def accept(p,t=2000,seq=1,state=RuntimePresenceState.WORKING):
    return accept_heartbeat(p,hb(p,seq,state),received_at_ms=t,expected_claim_id="c1",
      expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("auth"))

def test_join_uses_resident_receive_time_and_is_live():
    p=joined(t=10_000)
    assert p.last_seen_at_ms==10_000
    assert p.lease_expires_at_ms==55_000
    assert runtime_live(p,now_ms=55_000)

def test_worker_clock_cannot_extend_lease():
    p=joined()
    q=accept_heartbeat(p,hb(p,reported=(1<<53)-1),received_at_ms=2000,expected_claim_id="c1",
      expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("auth"))
    assert q.last_seen_at_ms==2000 and q.lease_expires_at_ms==47000

def test_replay_rejected():
    p=accept(joined())
    with pytest.raises(ContractViolation,match="strictly increase"):
        accept_heartbeat(p,hb(p,1),received_at_ms=3000,expected_claim_id="c1",
          expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("auth"))

@pytest.mark.parametrize("kind,msg", [("lease","lease generation"),("fence","fence mismatch")])
def test_stale_generation_or_fence_rejected(kind,msg):
    p=joined(); h=hb(p)
    data={**h.__dict__}
    data["lease_generation" if kind=="lease" else "fencing_token_digest"]=2 if kind=="lease" else d("bad")
    with pytest.raises(ContractViolation,match=msg):
        accept_heartbeat(p,HeartbeatV1(**data),received_at_ms=2000,expected_claim_id="c1",
          expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("auth"))

def test_claim_currentness_authority_fail_closed():
    p=joined()
    with pytest.raises(ContractViolation,match="claim mismatch"):
        accept_heartbeat(p,hb(p,claim="other"),received_at_ms=2000,expected_claim_id="c1",
          expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("auth"))
    with pytest.raises(ContractViolation,match="currentness mismatch"):
        accept_heartbeat(p,hb(p),received_at_ms=2000,expected_claim_id="c1",
          expected_currentness_digest=d("new"),expected_authority_ceiling_digest=d("auth"))
    with pytest.raises(ContractViolation,match="authority mismatch"):
        accept_heartbeat(p,hb(p),received_at_ms=2000,expected_claim_id="c1",
          expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("new"))

def test_late_heartbeat_does_not_resurrect_expired_lease():
    p=joined()
    with pytest.raises(ContractViolation,match="lease expired"):
        accept_heartbeat(p,hb(p),received_at_ms=p.lease_expires_at_ms+1,expected_claim_id="c1",
          expected_currentness_digest=d("cur"),expected_authority_ceiling_digest=d("auth"))

def test_stale_offline_boundaries():
    p=joined()
    assert effective_state(p,now_ms=p.lease_expires_at_ms)==RuntimePresenceState.READY
    assert effective_state(p,now_ms=p.lease_expires_at_ms+1)==RuntimePresenceState.STALE
    assert effective_state(p,now_ms=p.lease_expires_at_ms+p.recovery_grace_ms)==RuntimePresenceState.STALE
    assert effective_state(p,now_ms=p.lease_expires_at_ms+p.recovery_grace_ms+1)==RuntimePresenceState.OFFLINE

def test_reaper_and_rejoin_retire_old_fence():
    p=accept(joined())
    stale=reap_presence(p,now_ms=p.lease_expires_at_ms+1)
    assert stale.state==RuntimePresenceState.STALE and not stale.retire_fence
    t=p.lease_expires_at_ms+p.recovery_grace_ms+1
    dead=reap_presence(p,now_ms=t)
    assert dead.retire_fence and dead.release_claim and dead.requires_rejoin
    with pytest.raises(ContractViolation,match="strictly increase"):
        rejoin_runtime_worker(p,session_id="s2",lease_generation=1,fencing_token_digest=d("new"),received_at_ms=t,
          authority_ceiling_digest=d("auth"),currentness_digest=d("cur"))
    with pytest.raises(ContractViolation,match="new fencing token"):
        rejoin_runtime_worker(p,session_id="s2",lease_generation=2,fencing_token_digest=p.fencing_token_digest,received_at_ms=t,
          authority_ceiling_digest=d("auth"),currentness_digest=d("cur"))
    q=rejoin_runtime_worker(p,session_id="s2",lease_generation=2,fencing_token_digest=d("new"),received_at_ms=t,
      authority_ceiling_digest=d("auth"),currentness_digest=d("cur"))
    assert q.lease_generation==2 and q.state==RuntimePresenceState.READY and q.heartbeat_seq==0

def test_activity_observation_never_counts_as_runtime_live():
    a=ActivityObservationV1("chat","turn",1000,"drive-event")
    assert a.protected_body()["observation_kind"]=="ACTIVITY_OBSERVED"
    assert not runtime_live(a,now_ms=1000)

def test_census_distinguishes_working_reviewing_stale():
    p1=accept(joined("w1"),t=40000)
    p2=accept(joined("w2"),t=40000,state=RuntimePresenceState.REVIEWING)
    p3=joined("w3")
    now=p3.lease_expires_at_ms+1
    c=build_worker_census([p1,p2,p3],now_ms=now)
    assert (c.total_registered,c.live_count,c.working_count,c.reviewing_count,c.stale_count)==(3,2,1,1,1)
    assert c.utilization_basis_points==5000 and c.working_by_work_order==(("WO-C",1),)

def test_census_rejects_duplicate_worker():
    p=joined()
    with pytest.raises(ContractViolation,match="duplicate worker"):
        build_worker_census([p,p],now_ms=2000)

def test_census_digest_order_invariant():
    a,b=accept(joined("a")),accept(joined("b"))
    assert build_worker_census([a,b],now_ms=3000).digest()==build_worker_census([b,a],now_ms=3000).digest()

def test_census_does_not_expose_session_or_fence():
    p=accept(joined())
    body=build_worker_census([p],now_ms=3000).protected_body()
    text=repr(body)
    assert p.session_id not in text and p.fencing_token_digest not in text and "credential" not in text.lower()

def test_scheduler_projection_excludes_stale_and_has_no_authority_action():
    p1=accept(joined("a"),t=40000); p2=joined("b"); now=p2.lease_expires_at_ms+1
    body=scheduler_worker_projection([p1,p2],now_ms=now)
    assert body["active_worker_count"]==1 and body["logical_position_refs"]==["X"]
    assert set(body)=={"schema","active_worker_count","logical_position_refs","capability_profile_refs","evidence_independence_groups"}

def test_worker_cannot_self_assert_stale_offline():
    p=joined()
    for state in (RuntimePresenceState.STALE,RuntimePresenceState.OFFLINE):
        with pytest.raises(ContractViolation,match="self-assert"):
            hb(p,state=state).validate()

def test_control_characters_fail_closed():
    with pytest.raises(ContractViolation,match="control characters"):
        join_runtime_worker(worker_instance_id="w\n",session_id="s",model="m",provider="p",device_ref="d",runtime_ref="r",
          evidence_independence_group="e",lease_generation=1,fencing_token_digest=d("f"),received_at_ms=1,
          capability_profile_digest=d("c"),authority_ceiling_digest=d("a"),currentness_digest=d("x"))
