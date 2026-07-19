from __future__ import annotations

from pathlib import Path


SOURCE_PATH = Path("aura_source_integrity.py")
TEST_PATH = Path("tests/test_aura_source_integrity.py")

source = SOURCE_PATH.read_text(encoding="utf-8")
source_target = '''            current_bytes = handle.read(maximum_bytes + 1)
            if current_bytes != expected_bytes:
                raise _failure(
                    candidate,
                    code="SOURCE_CONTENT_CHANGED",
                    message=f"source bytes changed before write: {candidate}",
                    byte_offset=0,
                    offending=b"",
                    file_size=len(current_bytes),
                )
            handle.seek(0)
            handle.write(updated_bytes)
'''
source_replacement = '''            current_bytes = handle.read(maximum_bytes + 1)
            if current_bytes != expected_bytes:
                raise _failure(
                    candidate,
                    code="SOURCE_CONTENT_CHANGED",
                    message=f"source bytes changed before write: {candidate}",
                    byte_offset=0,
                    offending=b"",
                    file_size=len(current_bytes),
                )
            verified = os.fstat(handle.fileno())
            if not expected_identity.matches(verified):
                raise _failure(
                    candidate,
                    code="SOURCE_CONTENT_CHANGED",
                    message=(
                        "source identity changed immediately before write: "
                        f"{candidate}"
                    ),
                    byte_offset=0,
                    offending=b"",
                    file_size=verified.st_size,
                )
            handle.seek(0)
            handle.write(updated_bytes)
'''
if source.count(source_target) != 1:
    raise RuntimeError("source identity recheck target mismatch")
SOURCE_PATH.write_text(source.replace(source_target, source_replacement, 1), encoding="utf-8")

tests = TEST_PATH.read_text(encoding="utf-8")
import_target = "import copy\nfrom pathlib import Path\n"
import_replacement = "import copy\nimport os\nfrom pathlib import Path\n"
if tests.count(import_target) != 1:
    raise RuntimeError("test import target mismatch")
tests = tests.replace(import_target, import_replacement, 1)

marker = "\n\ndef test_boot_auditor_continues_after_post_read_failure(\n"
regression = '''

def test_identity_bound_write_rechecks_identity_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "module.py"
    path.write_text("value = 1\\n", encoding="utf-8")
    source, identity = read_utf8_source_with_identity(path)
    real_fstat = os.fstat
    fstat_calls = 0

    def mutate_same_inode_before_final_check(descriptor: int) -> os.stat_result:
        nonlocal fstat_calls
        fstat_calls += 1
        if fstat_calls == 2:
            path.write_text("value = 9\\n", encoding="utf-8")
        return real_fstat(descriptor)

    monkeypatch.setattr(os, "fstat", mutate_same_inode_before_final_check)

    with pytest.raises(SourceIntegrityError) as raised:
        write_utf8_source_if_unchanged(
            path,
            "value = 2\\n",
            expected_source=source,
            expected_identity=identity,
        )

    assert raised.value.failure.code == "SOURCE_CONTENT_CHANGED"
    assert path.read_text(encoding="utf-8") == "value = 9\\n"
'''
if tests.count(marker) != 1:
    raise RuntimeError("regression insertion target mismatch")
tests = tests.replace(marker, regression + marker, 1)
TEST_PATH.write_text(tests, encoding="utf-8")
