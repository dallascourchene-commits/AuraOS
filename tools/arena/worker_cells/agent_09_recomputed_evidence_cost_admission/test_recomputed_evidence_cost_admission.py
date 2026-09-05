import hashlib
import random
import unittest
from dataclasses import replace
from decimal import Decimal

from recomputed_evidence_cost_admission import *

HEAD='a'*40
RUNTIME=b'def route_topk(x):\n    return x\n'
RUNTIME_SHA=hashlib.sha256(RUNTIME).hexdigest()

def source(**kw):
    d=dict(source_head=HEAD,current_head=HEAD,runtime_path='/owner/glm_runtime.py',runtime_bytes=RUNTIME,expected_runtime_sha256=RUNTIME_SHA,source_generation='src-1',benchmark_generation='bench-1',hardware_fingerprint='host-1')
    d.update(kw); return SourceEvidence(**d)

def events(n=4):
    return tuple(FusedEvent(f'e{i}',f's{i}',i,7,(i%8,(i+1)%8)) for i in range(n))

def samples(n=4):
    return tuple(WorkloadSample(f's{i}','code' if i%2==0 else 'reasoning',f'prefix-{i}','src-1',True) for i in range(n))

def cost(n=4, *, spec_every=3, budget='1'):
    ts=[]
    for i in range(n):
        ts.append(TransferCharge(f't{i}',i+1,f'e{i}','SPECULATIVE' if i%spec_every==0 else 'DEMAND',1000+i))
    return CostEvidence('2.4',budget,1_000_000_000,tuple(ts))

class Tests(unittest.TestCase):
    def test_valid_composite(self):
        r=compile_composite(source(),events(),samples(),cost()); self.assertTrue(verify_composite(source(),events(),samples(),cost(),r))
    def test_no_source_currentness_boolean_exists(self): self.assertNotIn('source_current', SourceEvidence.__dataclass_fields__)
    def test_no_atomic_semantics_boolean_exists(self): self.assertNotIn('atomic_semantics_preserved', FusedEvent.__dataclass_fields__)
    def test_runtime_digest_recomputed(self):
        s=source(runtime_bytes=RUNTIME+b'#x');
        with self.assertRaisesRegex(AdmissionError,'DIGEST_MISMATCH'): compile_source(s)
    def test_stale_head_rejected(self):
        with self.assertRaisesRegex(AdmissionError,'STALE_SOURCE_HEAD'): compile_source(source(current_head='b'*40))
    def test_invalid_head_rejected(self):
        with self.assertRaisesRegex(AdmissionError,'INVALID_SOURCE_HEAD'): compile_source(source(source_head='x'))
    def test_empty_runtime_rejected(self):
        with self.assertRaisesRegex(AdmissionError,'RUNTIME_BYTES_REQUIRED'): compile_source(source(runtime_bytes=b''))
    def test_duplicate_event_id(self):
        es=list(events()); es[1]=replace(es[1],event_id='e0')
        with self.assertRaisesRegex(AdmissionError,'DUPLICATE_EVENT_ID'): compile_trace(es,compile_source(source()))
    def test_split_fused_slot_rejected(self):
        es=list(events()); es[1]=replace(es[1],sample_id='s0',token_index=0,layer=7)
        with self.assertRaisesRegex(AdmissionError,'SLOT_SPLIT'): compile_trace(es,compile_source(source()))
    def test_duplicate_native_expert_rejected(self):
        es=list(events()); es[0]=replace(es[0],native_experts=(1,1))
        with self.assertRaisesRegex(AdmissionError,'DUPLICATE_NATIVE_EXPERT'): compile_trace(es,compile_source(source()))
    def test_empty_experts_rejected(self):
        es=list(events()); es[0]=replace(es[0],native_experts=())
        with self.assertRaisesRegex(AdmissionError,'NATIVE_EXPERT_TUPLE_REQUIRED'): compile_trace(es,compile_source(source()))
    def test_workload_requires_trace(self):
        ss=list(samples()); ss.append(WorkloadSample('s99','code','p99','src-1',True))
        with self.assertRaisesRegex(AdmissionError,'MISSING_TRACE'): compile_workload(ss,compile_trace(events(),compile_source(source())),compile_source(source()))
    def test_trace_cannot_have_undeclared_sample(self):
        with self.assertRaisesRegex(AdmissionError,'UNDECLARED'): compile_workload(samples(3),compile_trace(events(4),compile_source(source())),compile_source(source()))
    def test_source_generation_cross_binding(self):
        ss=list(samples()); ss[0]=replace(ss[0],source_generation='src-2')
        with self.assertRaisesRegex(AdmissionError,'WORKLOAD_SOURCE_GENERATION_MISMATCH'): compile_workload(ss,compile_trace(events(),compile_source(source())),compile_source(source()))
    def test_prefix_collision_rejected(self):
        ss=list(samples()); ss[1]=replace(ss[1],rendered_prefix=ss[0].rendered_prefix)
        with self.assertRaisesRegex(AdmissionError,'PREFIX_COLLISION'): compile_composite(source(),events(),ss,cost())
    def test_shared_control_allowed(self):
        es=list(events()); ss=list(samples())
        es += [FusedEvent('e4','s4',4,7,(1,2)),FusedEvent('e5','s5',5,7,(2,3))]
        ss += [WorkloadSample('s4','code','shared','src-1',False,'shared-control'),WorkloadSample('s5','reasoning','shared','src-1',False,'shared-control')]
        r=compile_composite(source(),es,ss,cost(6)); self.assertTrue(r.efficiency_credit)
    def test_nonranking_requires_control_group(self):
        ss=list(samples()); ss[0]=replace(ss[0],ranking_eligible=False,control_group=None)
        with self.assertRaisesRegex(AdmissionError,'INVALID_STRING:control_group'): compile_composite(source(),events(),ss,cost())
    def test_ranking_sample_cannot_be_control(self):
        ss=list(samples()); ss[0]=replace(ss[0],control_group='x')
        with self.assertRaisesRegex(AdmissionError,'RANKING_SAMPLE_CANNOT_BE_CONTROL'): compile_composite(source(),events(),ss,cost())
    def test_duplicate_transfer_id(self):
        c=cost(); ts=list(c.transfers); ts[1]=replace(ts[1],transfer_id=ts[0].transfer_id)
        with self.assertRaisesRegex(AdmissionError,'DUPLICATE_PHYSICAL_TRANSFER_ID'): compile_composite(source(),events(),samples(),replace(c,transfers=tuple(ts)))
    def test_transfer_sequence_contiguous(self):
        c=cost(); ts=list(c.transfers); ts[1]=replace(ts[1],sequence=99)
        with self.assertRaisesRegex(AdmissionError,'NONCONTIGUOUS'): compile_composite(source(),events(),samples(),replace(c,transfers=tuple(ts)))
    def test_transfer_must_bind_trace_event(self):
        c=cost(); ts=list(c.transfers); ts[0]=replace(ts[0],event_id='missing')
        with self.assertRaisesRegex(AdmissionError,'TRANSFER_EVENT_NOT_IN_FUSED_TRACE'): compile_composite(source(),events(),samples(),replace(c,transfers=tuple(ts)))
    def test_lower_level_cost_recomputes_trace_parent(self):
        src=compile_source(source()); tr=compile_trace(events(),src)
        forged=replace(tr,event_root='f'*64)
        with self.assertRaisesRegex(AdmissionError,'TRACE_RECEIPT_RECOMPUTE_MISMATCH'):
            compile_cost(cost(),events(),src,forged)
    def test_lower_level_cost_binds_transfer_events(self):
        src=compile_source(source()); tr=compile_trace(events(),src); c=cost(); ts=list(c.transfers); ts[0]=replace(ts[0],event_id='missing')
        with self.assertRaisesRegex(AdmissionError,'TRANSFER_EVENT_NOT_IN_FUSED_TRACE'):
            compile_cost(replace(c,transfers=tuple(ts)),events(),src,tr)
    def test_bad_transfer_kind(self):
        c=cost(); ts=list(c.transfers); ts[0]=replace(ts[0],kind='MAGIC')
        with self.assertRaisesRegex(AdmissionError,'INVALID_TRANSFER_KIND'): compile_composite(source(),events(),samples(),replace(c,transfers=tuple(ts)))
    def test_exact_budget_boundary_1000(self):
        n=1000; es=tuple(FusedEvent(f'e{i}',f's{i}',i,0,(i%16,)) for i in range(n)); ss=tuple(WorkloadSample(f's{i}','a' if i%2==0 else 'b',f'p{i}','src-1',True) for i in range(n))
        ts=tuple(TransferCharge(f't{i}',i+1,f'e{i}','SPECULATIVE',232_647) for i in range(n)); budget=Decimal(sum(t.bytes_moved for t in ts))*Decimal('2.4')/Decimal(1_000_000_000)
        c=CostEvidence('2.4',format(budget,'f'),1_000_000_000,ts); r=compile_composite(source(),es,ss,c); self.assertEqual(r.speculative_bytes,232_647_000)
    def test_budget_one_byte_over_rejected(self):
        c=cost(); spec=sum(t.bytes_moved for t in c.transfers if t.kind=='SPECULATIVE'); exact=Decimal(spec)*Decimal('2.4')/Decimal(1_000_000_000); too_low=exact-Decimal('0.0000000001')
        with self.assertRaisesRegex(AdmissionError,'BUDGET_EXCEEDED'): compile_composite(source(),events(),samples(),replace(c,speculative_budget_j=format(too_low,'f')))
    def test_bool_not_int_for_bytes(self):
        c=cost(); ts=list(c.transfers); ts[0]=replace(ts[0],bytes_moved=True)
        with self.assertRaisesRegex(AdmissionError,'INVALID_INT'): compile_composite(source(),events(),samples(),replace(c,transfers=tuple(ts)))
    def test_nonfinite_decimal_rejected(self):
        with self.assertRaisesRegex(AdmissionError,'INVALID_DECIMAL'): compile_composite(source(),events(),samples(),replace(cost(),joules_per_gb='NaN'))
    def test_receipt_tamper_rejected(self):
        r=compile_composite(source(),events(),samples(),cost()); self.assertFalse(verify_composite(source(),events(),samples(),cost(),replace(r,total_bytes=r.total_bytes+1)))
    def test_authority_is_hard_false(self):
        r=compile_composite(source(),events(),samples(),cost()); self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)
    def test_omega8_exact_single_keeper(self):
        counts=exhaustive8(); self.assertEqual(sum(counts.values()),3**8); self.assertEqual(counts.get('ADMIT_D0_RECOMPUTED_EVIDENCE'),1)
    def test_13d_cannot_repair_invalid_core(self):
        rng=random.Random(8)
        for _ in range(5000):
            s=[rng.randrange(3) for _ in range(13)]; s[rng.randrange(7)]=0
            self.assertNotEqual(classify13(s),'ADMIT_D0_RECOMPUTED_EVIDENCE')
    def test_13d_tail_is_actually_evaluated(self):
        core=(2,2,2,2,2,2,2,1); self.assertEqual(classify13(core+(2,2,2,2,2)),'ADMIT_D0_RECOMPUTED_EVIDENCE'); self.assertEqual(classify13(core+(0,2,2,2,2)),'HOLD_TRAILING_CONTEXT_INVALID')

if __name__=='__main__': unittest.main()
