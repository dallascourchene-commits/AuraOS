"""One-time self-restoring trigger for the replay/probe finalizer."""
from pathlib import Path

_self = Path(__file__).resolve()
_body = _self.with_name("aura_open_weight_jacobian_adapter_body_once.py")
_source = _body.read_text(encoding="utf-8")
_self.write_text(_source, encoding="utf-8")
_body.unlink(missing_ok=True)
exec(compile(_source, str(_self), "exec"), globals(), globals())
