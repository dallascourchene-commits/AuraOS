# Contributing to Loru

Thanks for helping improve Loru. Keep changes focused, reproducible, and safe for an offline-first accessibility toolkit.

## Development setup

Loru requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\activate
pip install -e ".[dev,gui]"
```

For a backend-only change, `pip install -e ".[dev]"` is enough unless your change touches the GUI.

## Checks before opening a PR

Run the checks relevant to your change. The baseline development checks documented by the project are:

```bash
pytest -q
ruff check src tests
loru demo
```

If your change touches the Qt GUI, also run the GUI locally. Refresh screenshots with `python scripts/capture_gui_shots.py` only when the visible UI intentionally changes.

## Pull request checklist

- [ ] Keep the PR focused on one issue or coherent change.
- [ ] Add or update tests when behavior changes.
- [ ] Run `pytest -q` and `ruff check src tests`.
- [ ] Run `loru demo` when the offline sign-to-text / sign-to-voice path may be affected.
- [ ] Include screenshots or a short clip for UI changes.
- [ ] Include dataset license and consent notes for any new data or recordings.
- [ ] Do not commit secrets, credentials, private recordings, or generated local environments.
- [ ] Link the issue in the PR description (`Fixes #N` when appropriate).

## MergeOS bounty claim flow

If the issue is an MRG bounty, complete the repository's claim prerequisites **before** relying on the work as bounty-eligible:

1. Follow the `mergeos-bounties` organization.
2. Star `mergeos-bounties/mergeos`.
3. Star `mergeos-bounties/mergeos-contracts`.
4. Comment `I claim this bounty` on the Loru bounty issue.
5. Comment on MergeOS Claim Token issue #1 with the Loru issue link.
6. Open the PR against Loru's `master` branch and include `Fixes #N`.

The detailed, current bounty policy remains authoritative: [docs/BOUNTY.md](docs/BOUNTY.md). Issue titles can show marketing amounts; the MergeOS admin ledger uses its reviewed 25/50/100/200 MRG scale.

## Evidence

Make the review independently checkable. Backend and ML work should include tests and command output; UI work should include visual evidence; new datasets must include license/provenance notes. A passing local check is evidence for that check only, not proof of maintainer acceptance or payout.
