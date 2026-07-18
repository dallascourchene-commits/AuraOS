from __future__ import annotations

from pathlib import Path


def main() -> None:
    path = Path("aura_affordance_directory.py")
    text = path.read_text(encoding="utf-8")
    old = '''    except Exception:
        pass

    # Ground each affordance
'''
    new = '''    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        # AFFORDANCE_MAP enrichment is optional, but only expected read/shape
        # failures may fall back to the canonical seed directory.
        pass

    # Ground each affordance
'''
    if old not in text:
        raise SystemExit("optional affordance-map exception boundary not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
