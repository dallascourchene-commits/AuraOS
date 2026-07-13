#!/usr/bin/env python3
"""Create or update the public AuraOS Docker demo on Hugging Face Spaces.

Authentication is read from the locally saved Hugging Face token or the HF_TOKEN
environment variable. The token is never written to the deployment bundle.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create/update a public Docker Space containing the AuraOS demo bundle."
    )
    parser.add_argument(
        "--space-id",
        required=True,
        help="Hugging Face Space ID in USER/SPACE form, for example dallas/auraos-demo.",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create the Space as private. Hackathon submission normally needs a public Space.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print(
            "huggingface_hub is required. Install it with: "
            "python -m pip install 'huggingface_hub>=0.36,<2'",
            file=sys.stderr,
        )
        return 2

    bundle = Path(__file__).resolve().parents[1] / "deploy" / "huggingface-space"
    required = (bundle / "README.md", bundle / "Dockerfile")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(f"Deployment bundle is incomplete: {missing}", file=sys.stderr)
        return 2

    token = os.environ.get("HF_TOKEN") or None
    api = HfApi(token=token)

    repo_url = api.create_repo(
        repo_id=args.space_id,
        repo_type="space",
        space_sdk="docker",
        private=args.private,
        exist_ok=True,
    )
    commit = api.upload_folder(
        repo_id=args.space_id,
        repo_type="space",
        folder_path=bundle,
        commit_message="Deploy AuraOS public hackathon demo",
        delete_patterns=["Dockerfile", "README.md"],
    )

    namespace, name = args.space_id.split("/", 1)
    app_host = f"https://{namespace}-{name.replace('_', '-')}.hf.space"
    print(f"Space repository: {repo_url}")
    print(f"Deployment commit: {commit.commit_url}")
    print(f"Public app URL: {app_host}")
    print("Add FIREWORKS_API_KEY in Space Settings > Variables and secrets > Secrets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
