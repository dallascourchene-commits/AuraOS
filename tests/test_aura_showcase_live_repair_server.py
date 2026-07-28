from __future__ import annotations
import dataclasses
import hashlib
import json

from aura_bilateral_live_repair_foundry import BilateralIdentity
from aura_showcase_live_repair_server import (
    LiveRepairShowcaseState,
    _static_response,
    dispatch_live_repair_request,
)


def sha(value): return hashlib.sha256(value.encode()).hexdigest()
def sha1(value): return hashlib.sha1(value.encode()).hexdigest()
def identity():
    return BilateralIdentity(
        sha('intent'), 'intent-confirmation_'+sha('confirmation'), sha('ledger'), sha('guards'),
        'revision-1', sha1('head'), sha1('tree'), sha('profile'), 'verifier', sha('verifier-source'),
    )

def decoded(response):
    return response[0], json.loads(response[2].decode())

def test_showcase_status_and_existing_routes_are_composed(tmp_path):
    state=LiveRepairShowcaseState(tmp_path, demo_project='demo', auto_start=False)
    status,payload=decoded(dispatch_live_repair_request(state,'GET','/api/showcase/live-repair/status'))
    assert status == 200 and payload['ok'] is True
    assert payload['automatic_merge'] is False
    delegated_status, delegated=decoded(dispatch_live_repair_request(state,'GET','/api/showcase/projects'))
    assert delegated_status == 200 and delegated['ok'] is True
    assert delegated['default_project_id'] == 'winnipeg_pathways'
    assert len(delegated['projects']) == 4
    assert 'showcase_live_repair_version' not in delegated
    state.close()

def test_showcase_capture_route_is_explicit_and_versioned(tmp_path):
    state=LiveRepairShowcaseState(tmp_path, demo_project='demo', auto_start=False)
    status,started=decoded(dispatch_live_repair_request(state,'POST','/api/showcase/live-repair/capture/start',{
        'identity':dataclasses.asdict(identity()), 'release_id':'release', 'environment_id':'browser',
        'capture_authorized':True, 'max_events':4, 'retention_seconds':120,
    }))
    assert status == 200
    capture=started['capture_id']
    bad_status,bad=decoded(dispatch_live_repair_request(state,'POST',f'/api/showcase/live-repair/capture/{capture}/event/v2',{}))
    assert bad_status == 404 and bad['fail_closed'] is True
    state.close()

def test_static_index_injects_one_foundry_surface_and_authority_rail():
    status,content_type,body=_static_response('/index.html')
    assert status == 200 and content_type.startswith('text/html')
    assert body.count(b'data-tab="foundry"') == 1
    assert body.count(b'id="foundry-view"') == 1
    assert b'Confirmed human intent' in body
    assert b'P0 / P1 / current reproof' in body
    assert b'no learning promotion' in body
    assert b'live-repair-foundry.js' in body
    assert b'live-repair-foundry.css' in body


def test_browser_cannot_submit_forged_runtime_proof_or_rollback_adapter(tmp_path):
    item=identity()
    state=LiveRepairShowcaseState(
        tmp_path,
        demo_project='demo',
        auto_start=False,
        current_identity_resolver=lambda _captured: item,
    )
    _,started=decoded(dispatch_live_repair_request(state,'POST','/api/showcase/live-repair/capture/start',{
        'identity':dataclasses.asdict(item), 'release_id':'release', 'environment_id':'browser',
        'capture_authorized':True, 'max_events':4, 'retention_seconds':120,
    }))
    capture=started['capture_id']
    dispatch_live_repair_request(state,'POST',f'/api/showcase/live-repair/capture/{capture}/mark/v1',{'marker':'failure'})
    _,finalized=decoded(dispatch_live_repair_request(state,'POST',f'/api/showcase/live-repair/capture/{capture}/finalize/v1',{
        'current_identity':dataclasses.asdict(item),
        'expected_positive':['works'], 'expected_negative':['never hides failures'],
        'preservation_claims':['source remains unchanged'],
    }))
    packet_id=finalized['packet']['packet_id']
    attempt_status,attempt=decoded(dispatch_live_repair_request(state,'POST','/api/showcase/live-repair/attempt',{
        'packet_id':packet_id, 'current_identity':dataclasses.asdict(item),
        'candidate_digest':sha('candidate'), 'hypothesis':{'cause':'guess'},
        'runtime_proof':{'ok':True}, 'runtime_proof_ref':sha('not-retained'),
    }))
    assert attempt_status == 409
    assert 'not retained' in attempt['error']
    preview_status,preview=decoded(dispatch_live_repair_request(state,'POST','/api/showcase/live-repair/preview',{
        'packet_id':packet_id, 'current_identity':dataclasses.asdict(item),
        'candidate_digest':sha('candidate'), 'last_verified_digest':sha('verified'),
        'health_before':{'ok':True}, 'health_after':{'ok':False},
        'environment_class':'LOCAL_EPHEMERAL', 'rollback_preauthorized':True,
    }))
    assert preview_status == 409
    assert 'cannot manufacture a rollback adapter' in preview['error']
    state.close()
