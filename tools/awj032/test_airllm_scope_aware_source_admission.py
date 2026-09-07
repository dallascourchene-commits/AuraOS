import tempfile
from pathlib import Path
import unittest

from tools.awj032 import airllm_source_admission as v1
from tools.awj032 import airllm_scope_aware_source_admission as v2


def make_tree(root: Path, auto: str, version: str = '3.3.0'):
    pkg = root / 'air_llm' / 'airllm'
    pkg.mkdir(parents=True)
    (root / 'air_llm' / 'setup.py').write_text(
        f"from setuptools import setup\nsetup(name='airllm', version='{version}')\n",
        encoding='utf-8',
    )
    (pkg / 'auto_model.py').write_text(auto, encoding='utf-8')
    (pkg / 'base.py').write_text('def x():\n    return 1\n', encoding='utf-8')


class LexicalScopeGateTest(unittest.TestCase):
    def audit(self, source: str):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        make_tree(Path(td.name), source)
        return v1.audit_airllm_source(td.name), v2.audit_airllm_source(td.name)

    def test_cross_scope_same_name_false_positive_is_discharged(self):
        old,new=self.audit(
            "def build(model, attn):\n"
            "    kwargs = {'attn_implementation': attn, 'trust_remote_code': False}\n"
            "    return model.from_config(object(), **kwargs)\n"
            "def forward(*args, **kwargs):\n"
            "    return args, kwargs\n"
        )
        self.assertIn('REMOTE_CODE_OPAQUE_LOADER_KWARGS',{f.code for f in old.findings})
        self.assertEqual('PASS',new.status)
        self.assertEqual(1,len(new.discharged_findings))

    def test_line_movement_does_not_change_structural_discharge(self):
        _,new=self.audit(
            "\n\n\n"
            "def build(model, attn):\n"
            "    kwargs = {'trust_remote_code': False, 'attn_implementation': attn}\n"
            "    return model.from_config(object(), **kwargs)\n"
            "\n\n"
            "def generate(*args, **kwargs):\n"
            "    return args\n"
        )
        self.assertEqual('PASS',new.status)
        self.assertEqual(1,len(new.discharged_findings))

    def test_same_scope_caller_kwargs_remains_blocked(self):
        _,new=self.audit(
            "def build(model, **kwargs):\n"
            "    return model.from_config(object(), **kwargs)\n"
        )
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('REMOTE_CODE_OPAQUE_LOADER_KWARGS',{f.code for f in new.findings})
        self.assertEqual(0,len(new.discharged_findings))

    def test_same_scope_opaque_mapping_parameter_remains_blocked(self):
        _,new=self.audit(
            "def build(model, opts):\n"
            "    return model.from_pretrained('x', **opts)\n"
        )
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('REMOTE_CODE_OPAQUE_LOADER_KWARGS',{f.code for f in new.findings})

    def test_local_true_mapping_is_never_discharged(self):
        _,new=self.audit(
            "def build(model):\n"
            "    kwargs = {'trust_remote_code': True}\n"
            "    return model.from_config(object(), **kwargs)\n"
        )
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('REMOTE_CODE_TRUE',{f.code for f in new.findings})

    def test_local_dynamic_mapping_is_never_discharged(self):
        _,new=self.audit(
            "def build(model, trust):\n"
            "    kwargs = {'trust_remote_code': trust}\n"
            "    return model.from_config(object(), **kwargs)\n"
        )
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('REMOTE_CODE_DYNAMIC',{f.code for f in new.findings})

    def test_same_scope_opaque_update_remains_blocked(self):
        _,new=self.audit(
            "def build(model, extra):\n"
            "    kwargs = {'trust_remote_code': False}\n"
            "    kwargs.update(extra)\n"
            "    return model.from_config(object(), **kwargs)\n"
        )
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('REMOTE_CODE_OPAQUE_LOADER_KWARGS',{f.code for f in new.findings})

    def test_alias_opaque_mutation_remains_blocked(self):
        _,new=self.audit(
            "def build(model, key):\n"
            "    kwargs = {'trust_remote_code': False}\n"
            "    alias = kwargs\n"
            "    alias[key] = True\n"
            "    return model.from_config(object(), **kwargs)\n"
        )
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('REMOTE_CODE_OPAQUE_LOADER_KWARGS',{f.code for f in new.findings})

    def test_non_remote_findings_are_never_discharged(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        root=Path(td.name); make_tree(root,"def build(model):\n    return model.from_config(object(), trust_remote_code=False)\n")
        (root/'air_llm'/'airllm'/'base.py').write_text("# pip install unsafe\n",encoding='utf-8')
        new=v2.audit_airllm_source(root)
        self.assertEqual('BLOCKED',new.status)
        self.assertIn('NESTED_PIP_MUTATION',{f.code for f in new.findings})

    def test_receipt_preserves_source_identity(self):
        old,new=self.audit(
            "def build(model):\n"
            "    kwargs = {'trust_remote_code': False}\n"
            "    return model.from_config(object(), **kwargs)\n"
        )
        self.assertEqual(old.source_digest,new.source_digest)
        self.assertEqual(old.inspected_files,new.inspected_files)


if __name__=='__main__': unittest.main()
