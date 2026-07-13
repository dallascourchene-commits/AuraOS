from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "deploy" / "huggingface-space"
PINNED_REF = "611f80b9725a9b6f103e77f2849f6f90ee034836"


def test_space_app_card_declares_public_docker_runtime() -> None:
    card = (BUNDLE / "README.md").read_text(encoding="utf-8")
    assert "sdk: docker" in card
    assert "app_port: 7860" in card
    assert "AuraOS Sovereign Human-AI Arenas" in card
    assert "synthetic demonstration data" in card
    assert "FIREWORKS_API_KEY" in card
    assert PINNED_REF in card


def test_space_dockerfile_runs_reviewed_unified_showcase() -> None:
    dockerfile = (BUNDLE / "Dockerfile").read_text(encoding="utf-8")
    assert f"ARG AURA_REF={PINNED_REF}" in dockerfile
    assert "USER user" in dockerfile
    assert "EXPOSE 7860" in dockerfile
    assert '"aura_showcase_server.py"' in dockerfile
    assert '"--port", "7860"' in dockerfile
    assert '"--demo-project", "winnipeg_pathways"' in dockerfile
    assert "aura_secrets.json" not in dockerfile
    assert "FIREWORKS_API_KEY=" not in dockerfile
    assert "DEEPSEEK_API_KEY=" not in dockerfile


def test_publisher_requires_named_space_and_uploads_only_bundle() -> None:
    publisher = (ROOT / "scripts" / "deploy_huggingface_space.py").read_text(
        encoding="utf-8"
    )
    assert '"--space-id"' in publisher
    assert 'repo_type="space"' in publisher
    assert 'space_sdk="docker"' in publisher
    assert 'folder_path=bundle' in publisher
    assert 'private=args.private' in publisher
    assert "aura_secrets.json" not in publisher
    assert "FIREWORKS_API_KEY" in publisher


def test_deployment_docs_have_submission_field_and_no_localhost_url_claim() -> None:
    guide = (ROOT / "docs" / "AURA_PUBLIC_DEMO_PLATFORM.md").read_text(
        encoding="utf-8"
    )
    assert "Demo application platform: Hugging Face Spaces (Docker)" in guide
    assert "Do not enter `127.0.0.1` or `localhost`" in guide
    assert "hf.space" in guide
    assert "Variables and secrets" in guide
