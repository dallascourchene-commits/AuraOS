"""Nono-brokered launcher for Project006 Creator Studio media handoff.

Security boundary:
- the Arena/child receives only NONO's phantom value in
  HIGGSFIELD_API_CREDENTIAL;
- the real Higgsfield ID:SECRET is captured by NONO's supervisor-side
  credential_capture command and never enters this process;
- this launcher refuses the raw `ID:SECRET` shape and refuses to run unless
  HTTPS proxying is loopback-bound, preventing accidental direct-secret use.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlparse

from tools.project006.creator_media_handoff import (
    MediaHandoffError,
    MediaStatus,
    dispatch_media_handoff,
)

HIGGSFIELD_CREDENTIAL_ALIAS = "HIGGSFIELD_API_CREDENTIAL"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _nono_phantom_credential() -> str | None:
    """Return only a NONO-mediated phantom credential.

    Higgsfield's real developer credential is an `ID:SECRET` pair, so a colon
    in the child-visible value is treated as evidence that the raw credential
    leaked across the membrane and fails closed. A loopback HTTPS proxy is
    required so the phantom can only be redeemed by the local broker.
    """
    value = str(os.environ.get(HIGGSFIELD_CREDENTIAL_ALIAS) or "").strip()
    if not value or ":" in value:
        return None

    proxy = str(
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or ""
    ).strip()
    if not proxy:
        return None
    try:
        host = (urlparse(proxy).hostname or "").lower()
    except ValueError:
        return None
    if host not in _LOOPBACK_HOSTS:
        return None
    return value


def main() -> int:
    try:
        raw = json.load(sys.stdin)
        receipt = dispatch_media_handoff(
            raw,
            credential_resolver=_nono_phantom_credential,
        )
    except MediaHandoffError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    except Exception:
        print(
            json.dumps(
                {"ok": False, "error": "CREATOR_MEDIA_NONO_RUNNER_INTERNAL_FAILURE"},
                sort_keys=True,
            )
        )
        return 3

    ok = receipt.get("status") == MediaStatus.OK.value
    print(json.dumps({"ok": ok, "receipt": receipt}, sort_keys=True))
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
