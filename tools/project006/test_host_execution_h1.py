from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from host_execution_bridge import HostExecutionError, execute_observed_child
from host_receipt_registry import HostReceiptError, HostReceiptRegistry
from host_swarm_reducer import HostSwarmReductionError, validate_registry_backed_physical_swarm


class FakeExecutor:
    def __init__(self, events, text, provider="deepseek", model="deepseek-v4-flash"):
        self.events = events
        self.text = text
        self.provider = provider
        self.model = model
        self.calls = 0
    def generate(self, _prompt, **_kwargs):
        self.calls += 1
        self.events.append("generate")
        return self.text, None, 0.004


def target3_manifest():
    refs=[]
    for i,(role,worker) in enumerate((("A+","W-A"),("B-","W-B"),("C0","W-C"))):
        refs.append({"command_id":f"child-{i}","idempotency_key":f"idem-{i}","role_id":role,"worker_id":worker,"ordinal":i})
    m={
        "schema":"AuraPhysicalSwarmCompileReceiptV1",
        "parent_command_id":"parent",
        "parent_idempotency_key":"parent-idem",
        "parent_payload_digest":"c"*64,
        "target_size":3,
        "child_count":3,
        "child_refs":refs,
        "manifest_digest":"PENDING",
        "effect_started":False,
    }
    body={"schema":m["schema"],"parent_command_id":m["parent_command_id"],"parent_idempotency_key":m["parent_idempotency_key"],"parent_payload_digest":m["parent_payload_digest"],"target_size":m["target_size"],"children":m["child_refs"]}
    m["manifest_digest"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return m


def fake_route_validator(**kwargs):
    leaves=kwargs["child_receipts"]
    if len(leaves)!=3: raise AssertionError
    if len({x["attempt_id"] for x in leaves})!=3: raise AssertionError
    if len({x["provider_request_id"] for x in leaves})!=3: raise AssertionError
    if len({x["worker_id"] for x in leaves})!=3: raise AssertionError
    if len({x["role_id"] for x in leaves})!=3: raise AssertionError
    return {"physical_fanout_proven":True,"route_bound":True,"reduction_allowed":True}


class HostExecutionH1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.registry=HostReceiptRegistry(Path(self.tmp.name)/"registry.jsonl",host_instance_id="host-1",executor_id="executor-1")
        self.manifest=target3_manifest()
        self.plan=self.registry.allocate_plan(
            self.manifest,fanout_id="fanout-1",objective_id="work-1",source_generation="GEN25",
            command_digests_by_id={f"child-{i}": (str(i+1)*64)[:64] for i in range(3)},
        )
    def tearDown(self): self.tmp.cleanup()

    def test_fake_host_three_independent_calls_record_and_reduce(self):
        outputs={}
        executors=[]
        for i,child in enumerate(self.plan.children):
            events=[]
            ex=FakeExecutor(events,f"leaf-{i}")
            executors.append(ex)
            outputs[child["command_id"]]=execute_observed_child(
                registry=self.registry,plan=self.plan,child_identity=child,parent_command_id="parent",
                cohort_id="cohort-1",work_order_id="work-1",route_admission_digest=(f"{i+4:x}"*64)[:64],
                expected_provider="deepseek",expected_model="deepseek-v4-flash",executor=ex,prompt="bounded",
            )
            self.assertEqual(["generate"],events)
            self.assertEqual(1,ex.calls)
        out=validate_registry_backed_physical_swarm(
            registry=self.registry,plan=self.plan,model_outputs=outputs,
            expected_provider="deepseek",expected_model="deepseek-v4-flash",route_bound_validator=fake_route_validator,
        )
        self.assertTrue(out["physical_fanout_proven"])
        self.assertTrue(out["registry_authority_proven"])
        self.assertEqual(3,len(out["host_receipt_projection_digests"]))

    def test_replay_same_attempt_fails_before_second_generate(self):
        child=self.plan.children[0]
        events=[]; ex=FakeExecutor(events,"leaf")
        kwargs=dict(registry=self.registry,plan=self.plan,child_identity=child,parent_command_id="parent",cohort_id="cohort-1",work_order_id="work-1",route_admission_digest="d"*64,expected_provider="deepseek",expected_model="deepseek-v4-flash",executor=ex,prompt="bounded")
        execute_observed_child(**kwargs)
        with self.assertRaisesRegex(HostReceiptError,"RECEIPT_ID_REPLAY"):
            execute_observed_child(**kwargs)
        self.assertEqual(1,ex.calls)

    def test_wrong_executor_model_fails_before_registry_and_generate(self):
        child=self.plan.children[0]
        events=[]; ex=FakeExecutor(events,"leaf",model="deepseek-v4-pro")
        with self.assertRaisesRegex(HostExecutionError,"EXECUTOR_MODEL_ROUTE_MISMATCH"):
            execute_observed_child(registry=self.registry,plan=self.plan,child_identity=child,parent_command_id="parent",cohort_id="cohort-1",work_order_id="work-1",route_admission_digest="d"*64,expected_provider="deepseek",expected_model="deepseek-v4-flash",executor=ex,prompt="bounded")
        self.assertEqual(0,ex.calls)
        self.assertFalse(self.registry.path.exists())

    def test_caller_output_tamper_fails_digest_binding(self):
        outputs={}
        for i,child in enumerate(self.plan.children):
            ex=FakeExecutor([],f"leaf-{i}")
            outputs[child["command_id"]]=execute_observed_child(registry=self.registry,plan=self.plan,child_identity=child,parent_command_id="parent",cohort_id="cohort-1",work_order_id="work-1",route_admission_digest=(f"{i+4:x}"*64)[:64],expected_provider="deepseek",expected_model="deepseek-v4-flash",executor=ex,prompt="bounded")
        outputs[self.plan.children[1]["command_id"]]["result"]="tampered"
        with self.assertRaisesRegex(HostSwarmReductionError,"MODEL_OUTPUT_RESULT_DIGEST_MISMATCH"):
            validate_registry_backed_physical_swarm(registry=self.registry,plan=self.plan,model_outputs=outputs,expected_provider="deepseek",expected_model="deepseek-v4-flash",route_bound_validator=fake_route_validator)

    def test_free_form_receipts_have_no_reducer_parameter(self):
        import inspect
        sig=inspect.signature(validate_registry_backed_physical_swarm)
        self.assertNotIn("child_receipts",sig.parameters)
        self.assertNotIn("host_receipts",sig.parameters)


if __name__=="__main__": unittest.main()
