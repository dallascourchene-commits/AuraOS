from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile
import json
import unittest

import pr859_provenance_hardening_donor as d


def fixture():
    scene=b'scene'; scene_sha=sha256(scene).hexdigest()
    files={f'dummy/{i}.txt':{'bytes':1,'sha256':sha256(str(i).encode()).hexdigest()} for i in range(68)}
    files[d.ARCHIVE_SCENE_PATH]={'bytes':len(scene),'sha256':scene_sha}
    manifest={'schema':d.PROVENANCE_SCHEMA,'payload_file_count':69,'files':files}
    mb=json.dumps(manifest,indent=2).encode()
    bio=BytesIO()
    with ZipFile(bio,'w') as z:
        z.writestr(d.ARCHIVE_MANIFEST_PATH,mb); z.writestr(d.ARCHIVE_SCENE_PATH,scene)
    ab=bio.getvalue()
    binding={key:False for key in d.EXPECTED_BINDING_KEYS}
    binding.update({'strict_hold_unknown':True,'provenance_archive_sha256':sha256(ab).hexdigest()})
    route={'transitions':[{'transition_id':d.ROUTE_TRANSITION,'memory_city_binding':binding}]}
    rb=json.dumps(route).encode()
    return rb,mb,ab,manifest,scene_sha


class FakeBase:
    disposition=d.SeamDisposition.READY_FOR_INDEPENDENT_REVIEW
    reasons=()
    receipt_root='base'


class Tests(unittest.TestCase):
    def call(self, rb, mb, ab, manifest, scene_sha):
        with patch.object(d,'ARCHIVE_SHA256',sha256(ab).hexdigest()), \
             patch.object(d,'PROVENANCE_MANIFEST_SHA256',sha256(mb).hexdigest()), \
             patch.object(d,'PROVENANCE_MANIFEST_CANONICAL_ROOT',d._root(manifest)), \
             patch.object(d,'SCENE_SOURCE_SHA256',scene_sha), \
             patch.object(d,'validate_spatial_seam',return_value=FakeBase()):
            return d.validate_hardened(rb,mb,ab)

    def test_synthetic_exact_chain_ready(self):
        x=fixture(); self.assertEqual(self.call(*x).disposition,d.SeamDisposition.READY_FOR_INDEPENDENT_REVIEW)
    def test_duplicate_transition_holds(self):
        rb,mb,ab,m,s=fixture(); r=json.loads(rb); r['transitions'].append(deepcopy(r['transitions'][0])); out=self.call(json.dumps(r).encode(),mb,ab,m,s); self.assertIn('COMPILE_SCENE_TRANSITION_NOT_EXACTLY_ONE',out.reasons)
    def test_nonlist_transition_holds(self):
        rb,mb,ab,m,s=fixture(); r=json.loads(rb); r['transitions']={}; out=self.call(json.dumps(r).encode(),mb,ab,m,s); self.assertIn('TRANSITIONS_LIST_REQUIRED',out.reasons)
    def test_malformed_transition_holds(self):
        rb,mb,ab,m,s=fixture(); r=json.loads(rb); r['transitions'].insert(0,'bad'); out=self.call(json.dumps(r).encode(),mb,ab,m,s); self.assertIn('TRANSITION_ENTRY_INVALID:0',out.reasons)
    def test_unknown_binding_holds(self):
        rb,mb,ab,m,s=fixture(); r=json.loads(rb); r['transitions'][0]['memory_city_binding']['x']=False; out=self.call(json.dumps(r).encode(),mb,ab,m,s); self.assertIn('UNKNOWN_BINDING_KEY:x',out.reasons)
    def test_manifest_membership_holds(self):
        rb,mb,ab,m,s=fixture(); mb2=mb+b' '; out=self.call(rb,mb2,ab,m,s); self.assertIn('ARCHIVE_MANIFEST_MEMBERSHIP_MISMATCH',out.reasons)
    def test_archive_mutation_holds(self):
        rb,mb,ab,m,s=fixture(); ab2=bytearray(ab); ab2[-1]^=1
        with patch.object(d,'ARCHIVE_SHA256',sha256(ab).hexdigest()), \
             patch.object(d,'PROVENANCE_MANIFEST_SHA256',sha256(mb).hexdigest()), \
             patch.object(d,'PROVENANCE_MANIFEST_CANONICAL_ROOT',d._root(m)), \
             patch.object(d,'SCENE_SOURCE_SHA256',s), \
             patch.object(d,'validate_spatial_seam',return_value=FakeBase()):
            out=d.validate_hardened(rb,mb,bytes(ab2))
        self.assertIn('PROVENANCE_ARCHIVE_BYTES_MISMATCH',out.reasons)

if __name__=='__main__': unittest.main()
