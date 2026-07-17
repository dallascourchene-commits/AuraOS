"""Apply verified manual hardening to the Phase 4 persistence engine."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one hardening anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, sentinel: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if sentinel in text:
        return
    target.write_text(text.rstrip() + "\n\n" + content.rstrip() + "\n", encoding="utf-8")


def patch_engine() -> None:
    path = "aura_temporal_persistence.py"
    replace_once(path, "import json\nimport os\n", "import json\nimport math\nimport os\n")
    replace_once(
        path,
        '        if type(self.created_at) not in {int, float}:\n'
        '            raise ValueError("created_at must be numeric")\n',
        '        if (\n'
        '            type(self.created_at) not in {int, float}\n'
        '            or not math.isfinite(float(self.created_at))\n'
        '            or float(self.created_at) < 0\n'
        '        ):\n'
        '            raise ValueError("created_at must be finite and non-negative")\n',
    )
    replace_once(
        path,
        '        expected_record = digest(\n'
        '            {"identity": expected_identity, "payload": payload},\n'
        '            size=20,\n'
        '        )\n',
        '        expected_record = digest(\n'
        '            {\n'
        '                "identity": expected_identity,\n'
        '                "payload": payload,\n'
        '                "created_at": float(self.created_at),\n'
        '            },\n'
        '            size=20,\n'
        '        )\n',
    )
    old_lock = '''    @contextmanager
    def _lock(self, *, create: bool = True) -> Iterator[None]:
        if not self.root.exists() and not create:
            yield
            return
        self.root.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")
        try:
            try:
                import fcntl  # type: ignore

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass
            yield
        finally:
            try:
                import fcntl  # type: ignore

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            handle.close()
'''
    new_lock = '''    @contextmanager
    def _lock(self, *, create: bool = True) -> Iterator[None]:
        if not self.root.exists() and not create:
            yield
            return
        self.root.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")
        backend = ""
        lock_module: Any = None
        try:
            try:
                import fcntl  # type: ignore
            except ImportError:
                fcntl = None  # type: ignore[assignment]
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                backend = "fcntl"
                lock_module = fcntl
            else:
                try:
                    import msvcrt  # type: ignore
                except ImportError as exc:
                    raise RuntimeError("platform does not provide a supported file lock") from exc
                handle.seek(0)
                if not handle.read(1):
                    handle.write("0")
                    handle.flush()
                    os.fsync(handle.fileno())
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                backend = "msvcrt"
                lock_module = msvcrt
        except OSError as exc:
            handle.close()
            raise RuntimeError("failed to acquire temporal registry lock") from exc
        try:
            yield
        finally:
            try:
                if backend == "fcntl":
                    lock_module.flock(handle.fileno(), lock_module.LOCK_UN)
                elif backend == "msvcrt":
                    handle.seek(0)
                    lock_module.locking(handle.fileno(), lock_module.LK_UNLCK, 1)
            finally:
                handle.close()
'''
    replace_once(path, old_lock, new_lock)
    replace_once(
        path,
        '''    def verify_registry(self) -> dict[str, Any]:
        with self._lock(create=False):
            entries = self._registry_entries_unlocked()
        return {
            "ok": True,
            "version": TEMPORAL_REGISTRY_VERSION,
            "entry_count": len(entries),
            "last_entry_digest": entries[-1]["entry_digest"] if entries else "",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
''',
        '''    def verify_registry(self) -> dict[str, Any]:
        with self._lock(create=False):
            entries = self._registry_entries_unlocked()
            for entry in entries:
                self._load_from_entry_unlocked(entry)
        return {
            "ok": True,
            "version": TEMPORAL_REGISTRY_VERSION,
            "entry_count": len(entries),
            "verified_checkpoint_count": len(entries),
            "last_entry_digest": entries[-1]["entry_digest"] if entries else "",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
''',
    )
    replace_once(
        path,
        '        generated_at = float(time.time() if created_at is None else created_at)\n'
        '        if not generated_at >= 0:\n'
        '            raise ValueError("created_at must be non-negative")\n',
        '        generated_at = float(time.time() if created_at is None else created_at)\n'
        '        if not math.isfinite(generated_at) or generated_at < 0:\n'
        '            raise ValueError("created_at must be finite and non-negative")\n',
    )
    replace_once(
        path,
        '            record_digest = digest(\n'
        '                {"identity": identity, "payload": normalized_payload},\n'
        '                size=20,\n'
        '            )\n',
        '            record_digest = digest(\n'
        '                {\n'
        '                    "identity": identity,\n'
        '                    "payload": normalized_payload,\n'
        '                    "created_at": generated_at,\n'
        '                },\n'
        '                size=20,\n'
        '            )\n',
    )
    old_load = '''        checkpoint = TemporalCheckpoint.from_dict(value)
        if checkpoint.checkpoint_id != entry.get("checkpoint_id"):
            raise ValueError("registry checkpoint ID does not match checkpoint file")
        if checkpoint.record_digest != entry.get("record_digest"):
            raise ValueError("registry record digest does not match checkpoint file")
        return checkpoint
'''
    new_load = '''        checkpoint = TemporalCheckpoint.from_dict(value)
        expected_path = self._checkpoint_path(checkpoint).relative_to(self.repo_root).as_posix()
        expected_entry = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "arena_id": checkpoint.arena_id,
            "session_id": checkpoint.session_id,
            "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
            "branch_name": checkpoint.branch_name,
            "sequence_number": checkpoint.sequence_number,
            "repo_head": checkpoint.repo_head,
            "created_at": checkpoint.created_at,
            "checkpoint_path": expected_path,
            "record_digest": checkpoint.record_digest,
        }
        for key, expected in expected_entry.items():
            if entry.get(key) != expected:
                raise ValueError(f"registry {key} does not match checkpoint file")
        return checkpoint
'''
    replace_once(path, old_load, new_load)
    replace_once(
        path,
        '            payload=payload or parent.payload,\n',
        '            payload=parent.payload if payload is None else payload,\n',
    )


def patch_tests() -> None:
    append_once(
        "tests/test_aura_temporal_persistence.py",
        "def test_registry_verification_checks_checkpoint_files_and_metadata",
        '''def test_registry_verification_checks_checkpoint_files_and_metadata(tmp_path: Path):
    from aura_refactor_state_identity import digest

    registry = _registry(tmp_path)
    result = _write(registry)
    entry = dict(result["registry_entry"])
    path = tmp_path / entry["checkpoint_path"]
    path.unlink()
    with pytest.raises(ValueError, match="checkpoint file is missing or invalid"):
        registry.verify_registry()

    registry = TemporalCheckpointRegistry(tmp_path / "metadata")
    result = _write(registry)
    registry_path = registry.registry_path
    entry = json.loads(registry_path.read_text(encoding="utf-8"))
    body = {key: value for key, value in entry.items() if key != "entry_digest"}
    body["arena_id"] = "human_agent_arena"
    entry = {**body, "entry_digest": digest(body, size=20)}
    registry_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="registry arena_id does not match"):
        registry.verify_registry()


def test_fork_preserves_explicit_empty_payload(tmp_path: Path):
    registry = _registry(tmp_path)
    root = _write(registry)
    forked = registry.fork_checkpoint(
        root["checkpoint"]["checkpoint_id"],
        branch_name="empty-scenario",
        payload={},
        created_at=11.0,
    )
    assert forked["checkpoint"]["payload"] == {}


@pytest.mark.parametrize("created_at", [float("inf"), float("-inf"), float("nan")])
def test_nonfinite_checkpoint_times_are_rejected(tmp_path: Path, created_at: float):
    registry = _registry(tmp_path)
    with pytest.raises(ValueError, match="created_at must be finite and non-negative"):
        _write(registry, created_at=created_at)
''',
    )


def main() -> None:
    patch_engine()
    patch_tests()


if __name__ == "__main__":
    main()
