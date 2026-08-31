import importlib.util
import sys
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'tools' / 'creator_studio' / 'neutral_timeline_contract.py'
spec = importlib.util.spec_from_file_location('neutral_timeline_contract', MODULE)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def asset(asset_id: str, *, tags=('Urban', 'Night'), evidence='drive:receipt:1', uri='file:///tmp/a.mov'):
    return mod.AdmittedAssetRefV1(
        asset_id=asset_id,
        uri=uri,
        evidence_ref=evidence,
        media_type='video',
        tags=tuple(tags),
    )


class CreatorTimelineContractTests(unittest.TestCase):
    def test_tag_identity_is_permutation_duplicate_case_whitespace_invariant(self):
        a = mod.tag_set_fingerprint([' Urban ', 'NIGHT', 'urban'])
        b = mod.tag_set_fingerprint(['night', 'urban'])
        c = mod.tag_set_fingerprint(['URBAN', '  night  '])
        self.assertEqual(a, b)
        self.assertEqual(b, c)
        self.assertEqual(mod.canonical_tag_set(['NIGHT', 'urban', 'night']), ('night', 'urban'))

    def test_length_prefix_prevents_concatenation_ambiguity(self):
        self.assertNotEqual(
            mod.tag_set_fingerprint(['ab', 'c']),
            mod.tag_set_fingerprint(['a', 'bc']),
        )

    def test_composition_identity_excludes_uri_evidence_and_tag_metadata(self):
        clip_a = mod.TimelineClipV1('c1', asset('asset-1'), 0, 48)
        clip_b = mod.TimelineClipV1(
            'c1',
            asset('asset-1', tags=('different',), evidence='drive:receipt:2', uri='s3://bucket/relocated.mov'),
            0,
            48,
        )
        t1 = mod.CreatorTimelineV1('Edit', 24, 1, (clip_a,))
        t2 = mod.CreatorTimelineV1('Edit', 24, 1, (clip_b,))
        self.assertEqual(t1.composition_digest, t2.composition_digest)
        self.assertNotEqual(t1.evidence_binding_digest, t2.evidence_binding_digest)

    def test_clip_sequence_changes_composition_identity(self):
        c1 = mod.TimelineClipV1('c1', asset('asset-1'), 0, 24)
        c2 = mod.TimelineClipV1('c2', asset('asset-2'), 12, 48)
        a = mod.CreatorTimelineV1('Edit', 24, 1, (c1, c2))
        b = mod.CreatorTimelineV1('Edit', 24, 1, (c2, c1))
        self.assertNotEqual(a.composition_digest, b.composition_digest)

    def test_invalid_timing_fails_closed(self):
        with self.assertRaises(mod.TimelineContractError):
            mod.TimelineClipV1('c1', asset('asset-1'), -1, 24)
        with self.assertRaises(mod.TimelineContractError):
            mod.TimelineClipV1('c1', asset('asset-1'), 0, 0)

    def test_duplicate_clip_ids_fail_closed(self):
        c1 = mod.TimelineClipV1('same', asset('asset-1'), 0, 24)
        c2 = mod.TimelineClipV1('same', asset('asset-2'), 0, 24)
        with self.assertRaises(mod.TimelineContractError):
            mod.CreatorTimelineV1('Edit', 24, 1, (c1, c2))

    def test_otio_roundtrip_preserves_order_timing_asset_and_digests(self):
        c1 = mod.TimelineClipV1('intro', asset('asset-1'), 10, 48)
        c2 = mod.TimelineClipV1('body', asset('asset-2', uri='file:///tmp/b.mov'), 120, 72)
        timeline = mod.CreatorTimelineV1('Edit', 24000, 1001, (c1, c2))
        payload = timeline.to_otio_json()
        receipt = mod.validate_otio_roundtrip(timeline, payload)
        self.assertTrue(receipt['otio_roundtrip_equivalent'])
        self.assertTrue(receipt['clip_order_preserved'])
        self.assertTrue(receipt['timing_preserved'])
        self.assertTrue(receipt['asset_identity_preserved'])
        self.assertFalse(receipt['provider_specific_fields_in_composition_identity'])
        self.assertFalse(receipt['capcut_private_draft_compatibility_proven'])
        self.assertFalse(receipt['asset_verification_minted_by_timeline_layer'])
        self.assertFalse(receipt['semantic_k27_authority'])
        self.assertFalse(receipt['native_transformer_kv_accessed'])

    def test_media_type_and_empty_tags_are_bounded(self):
        with self.assertRaises(mod.TimelineContractError):
            mod.AdmittedAssetRefV1('a', 'file:///x', 'e', 'document', ('tag',))
        with self.assertRaises(mod.TimelineContractError):
            mod.AdmittedAssetRefV1('a', 'file:///x', 'e', 'video', ())


if __name__ == '__main__':
    unittest.main()
