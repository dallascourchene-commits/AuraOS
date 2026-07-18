from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile.aura-gate"
COMPOSE_FILE = REPO_ROOT / "docker-compose.aura-gate.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _required_variable(text: str, name: str) -> bool:
    return re.search(rf"\$\{{{re.escape(name)}:\?[^}}]+\}}", text) is not None


def _read_only_bind(text: str, variable: str, target: str) -> bool:
    pattern = (
        r"- type: bind\s+"
        rf"source: \"\$\{{{re.escape(variable)}:\?[^}}]+\}}\"\s+"
        rf"target: {re.escape(target)}\s+"
        r"read_only: true"
    )
    return re.search(pattern, text) is not None


def _deployment_errors(dockerfile: str, compose: str) -> set[str]:
    errors: set[str] = set()

    if re.search(r"^ARG AURA_GATE_BASE_IMAGE=", dockerfile, re.MULTILINE):
        errors.add("base_arg_default")
    if "ARG AURA_GATE_BASE_IMAGE\nFROM ${AURA_GATE_BASE_IMAGE} AS aura-gate-runtime" not in dockerfile:
        errors.add("base_not_required")
    if "re.fullmatch(r'[^@\\s]+@sha256:[0-9a-f]{64}', value)" not in dockerfile:
        errors.add("base_digest_guard_missing")
    if re.search(r"^FROM (?!\$\{AURA_GATE_BASE_IMAGE\})", dockerfile, re.MULTILINE):
        errors.add("literal_base_image")
    if "USER 65532:65532" not in dockerfile or re.search(r"^USER (?:0|root)(?::|$)", dockerfile, re.MULTILINE):
        errors.add("nonroot_user_missing")
    if 'ENTRYPOINT ["python", "-B", "-m", "aura_gate_server"]' not in dockerfile:
        errors.add("entrypoint_not_minimal")
    if re.search(r"^(?:COPY|ADD)\s", dockerfile, re.MULTILINE):
        errors.add("source_embedded")
    if 'user: "65532:65532"' not in compose:
        errors.add("compose_nonroot_user_missing")
    if re.search(r"^\s+(?:command|entrypoint):", compose, re.MULTILINE):
        errors.add("compose_process_override")

    required_variables = {
        "AURA_GATE_REPO_ROOT",
        "AURA_GATE_BASE_IMAGE",
        "AURA_GATE_POLICY_FILE",
        "AURA_GATE_OIDC_FILE",
        "AURA_GATE_JWKS_FILE",
        "AURA_GATE_ACTOR_SALT_FILE",
        "AURA_GATE_POLICY_ID",
        "AURA_GATE_PORT",
        "AURA_GATE_MEMORY_LIMIT",
        "AURA_GATE_CPU_LIMIT",
        "AURA_GATE_STATE_VOLUME",
        "AURA_GATE_AUDIT_VOLUME",
        "AURA_GATE_SIEM_VOLUME",
        "AURA_GATE_STAGING_ROOT",
    }
    for name in required_variables:
        if not _required_variable(compose, name):
            errors.add(f"required_variable_missing:{name}")
    if any(":?" not in match for match in re.findall(r"\$\{[^}]+\}", compose)):
        errors.add("optional_interpolation")

    if "network_mode: host" not in compose:
        errors.add("host_network_missing")
    if 'AURA_GATE_HOST: "127.0.0.1"' not in compose:
        errors.add("loopback_bind_missing")
    if "0.0.0.0" in compose or "::" in compose:
        errors.add("public_bind")
    if re.search(r"^\s+ports:\s*$", compose, re.MULTILINE):
        errors.add("published_ports")
    if re.search(r"^\s+expose:\s*$", compose, re.MULTILINE):
        errors.add("exposed_ports")

    for variable, target in (
        ("AURA_GATE_REPO_ROOT", "/opt/aura/repo"),
        ("AURA_GATE_POLICY_FILE", "/run/aura-gate/policy.json"),
        ("AURA_GATE_OIDC_FILE", "/run/aura-gate/oidc.json"),
        ("AURA_GATE_JWKS_FILE", "/run/aura-gate/jwks.json"),
        ("AURA_GATE_ACTOR_SALT_FILE", "/run/aura-gate/actor-salt"),
    ):
        if not _read_only_bind(compose, variable, target):
            errors.add(f"read_only_bind_missing:{variable}")
    if not re.search(
        r"- type: volume\s+source: aura_gate_state\s+target: /var/lib/aura-gate/state",
        compose,
    ):
        errors.add("state_volume_missing")
    if not re.search(
        r"- type: volume\s+source: aura_gate_audit\s+target: /var/lib/aura-gate/audit",
        compose,
    ):
        errors.add("audit_volume_missing")
    if not re.search(
        r"- type: volume\s+source: aura_gate_siem\s+target: /var/lib/aura-gate/siem",
        compose,
    ):
        errors.add("siem_volume_missing")
    if not re.search(
        r'- type: bind\s+source: "\$\{AURA_GATE_STAGING_ROOT:\?[^}]+\}"\s+'
        r"target: /opt/aura/repo/Aura_Staging(?:\s+read_only: true)?",
        compose,
    ):
        errors.add("staging_bind_missing")
    if re.search(
        r'- type: bind\s+source: "\$\{AURA_GATE_STAGING_ROOT:\?[^}]+\}"\s+'
        r"target: /opt/aura/repo/Aura_Staging\s+read_only: true",
        compose,
    ):
        errors.add("staging_bind_read_only")
    if (
        compose.count("target: /var/lib/aura-gate/state") != 1
        or compose.count("target: /var/lib/aura-gate/audit") != 1
        or compose.count("target: /var/lib/aura-gate/siem") != 1
    ):
        errors.add("state_audit_not_separate")
    if (
        'name: "${AURA_GATE_STATE_VOLUME:?' not in compose
        or 'name: "${AURA_GATE_AUDIT_VOLUME:?' not in compose
        or 'name: "${AURA_GATE_SIEM_VOLUME:?' not in compose
    ):
        errors.add("durable_volume_names_missing")

    if "AURA_GATE_ACTOR_SALT_FILE: /run/aura-gate/actor-salt" not in compose:
        errors.add("actor_salt_runtime_path_missing")

    hardening = {
        "read_only_root_missing": "    read_only: true\n    tmpfs:",
        "tmpfs_hardening_missing": "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
        "cap_drop_missing": "cap_drop:\n      - ALL",
        "no_new_privileges_missing": "no-new-privileges:true",
        "init_missing": "init: true",
        "pids_limit_missing": "pids_limit: 128",
        "memory_limit_missing": 'mem_limit: "${AURA_GATE_MEMORY_LIMIT:?',
        "memory_swap_limit_missing": 'memswap_limit: "${AURA_GATE_MEMORY_LIMIT:?',
        "cpu_limit_missing": 'cpus: "${AURA_GATE_CPU_LIMIT:?',
        "restart_policy_missing": 'restart: "no"',
        "healthcheck_missing": "\n    healthcheck:\n",
        "loopback_healthcheck_missing": "http://127.0.0.1:",
    }
    for code, fragment in hardening.items():
        if fragment not in compose:
            errors.add(code)

    lowered = f"{dockerfile}\n{compose}".lower()
    if ":latest" in lowered or "@latest" in lowered:
        errors.add("mutable_latest_image")
    if "privileged: true" in lowered:
        errors.add("privileged_container")
    if re.search(r"(?im)^\s*(?:password|api[_-]?key|bearer[_-]?token)\s*:", compose):
        errors.add("literal_credential")
    return errors


def test_deployment_contract_is_complete_and_fail_closed() -> None:
    assert _deployment_errors(_text(DOCKERFILE), _text(COMPOSE_FILE)) == set()


@pytest.mark.parametrize(
    ("artifact", "old", "new", "expected"),
    [
        (
            "dockerfile",
            "ARG AURA_GATE_BASE_IMAGE\nFROM",
            "ARG AURA_GATE_BASE_IMAGE=python:3.12-slim\nFROM",
            "base_arg_default",
        ),
        (
            "dockerfile",
            "r'[^@\\s]+@sha256:[0-9a-f]{64}'",
            "r'.+'",
            "base_digest_guard_missing",
        ),
        (
            "dockerfile",
            "FROM ${AURA_GATE_BASE_IMAGE} AS aura-gate-runtime",
            "FROM python:3.12-slim AS aura-gate-runtime",
            "base_not_required",
        ),
        ("dockerfile", "USER 65532:65532", "USER root", "nonroot_user_missing"),
        (
            "dockerfile",
            'ENTRYPOINT ["python", "-B", "-m", "aura_gate_server"]',
            'ENTRYPOINT ["sh", "-c", "python -m aura_gate_server"]',
            "entrypoint_not_minimal",
        ),
        (
            "compose",
            'user: "65532:65532"',
            'user: "0:0"',
            "compose_nonroot_user_missing",
        ),
        (
            "compose",
            "    working_dir: /opt/aura/repo",
            '    working_dir: /opt/aura/repo\n    command: ["sh"]',
            "compose_process_override",
        ),
        (
            "dockerfile",
            "WORKDIR /opt/aura/repo",
            "COPY . /opt/aura/repo\nWORKDIR /opt/aura/repo",
            "source_embedded",
        ),
        ("compose", "network_mode: host", "network_mode: bridge", "host_network_missing"),
        (
            "compose",
            'AURA_GATE_HOST: "127.0.0.1"',
            'AURA_GATE_HOST: "0.0.0.0"',
            "public_bind",
        ),
        (
            "compose",
            "    network_mode: host",
            '    network_mode: host\n    ports:\n      - "8765:8765"',
            "published_ports",
        ),
        (
            "compose",
            "    network_mode: host",
            '    network_mode: host\n    expose:\n      - "8765"',
            "exposed_ports",
        ),
        (
            "compose",
            "  aura-gate:\n",
            "  aura-gate:\n    image: vendor/aura-gate:latest\n",
            "mutable_latest_image",
        ),
        (
            "compose",
            '      PYTHONUNBUFFERED: "1"',
            '      PYTHONUNBUFFERED: "1"\n      API_KEY: literal-secret',
            "literal_credential",
        ),
        (
            "compose",
            'AURA_GATE_PORT: "${AURA_GATE_PORT:?set the loopback Aura Gate port}"',
            'AURA_GATE_PORT: "8765"',
            "required_variable_missing:AURA_GATE_PORT",
        ),
        (
            "compose",
            "target: /opt/aura/repo\n        read_only: true",
            "target: /opt/aura/repo\n        read_only: false",
            "read_only_bind_missing:AURA_GATE_REPO_ROOT",
        ),
        (
            "compose",
            "    read_only: true\n    tmpfs:",
            "    read_only: false\n    tmpfs:",
            "read_only_root_missing",
        ),
        (
            "compose",
            "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
            "/tmp:rw,size=16m,mode=1777",
            "tmpfs_hardening_missing",
        ),
        ("compose", "cap_drop:\n      - ALL", "cap_drop:\n      - NET_ADMIN", "cap_drop_missing"),
        (
            "compose",
            "no-new-privileges:true",
            "no-new-privileges:false",
            "no_new_privileges_missing",
        ),
        ("compose", "init: true", "init: false", "init_missing"),
        ("compose", "pids_limit: 128", "pids_limit: 0", "pids_limit_missing"),
        (
            "compose",
            'mem_limit: "${AURA_GATE_MEMORY_LIMIT:?set a Docker memory limit such as 1g}"',
            'memory_hint: "1g"',
            "memory_limit_missing",
        ),
        (
            "compose",
            'cpus: "${AURA_GATE_CPU_LIMIT:?set a Docker CPU limit such as 1.0}"',
            'cpu_hint: "1.0"',
            "cpu_limit_missing",
        ),
        (
            "compose",
            "    read_only: true\n    tmpfs:",
            "    privileged: true\n    read_only: true\n    tmpfs:",
            "privileged_container",
        ),
        (
            "compose",
            "target: /run/aura-gate/actor-salt\n        read_only: true",
            "target: /run/aura-gate/actor-salt\n        read_only: false",
            "read_only_bind_missing:AURA_GATE_ACTOR_SALT_FILE",
        ),
        (
            "compose",
            "target: /var/lib/aura-gate/audit",
            "target: /var/lib/aura-gate/state",
            "state_audit_not_separate",
        ),
        ("compose", "healthcheck:", "disabled_healthcheck:", "healthcheck_missing"),
        ("compose", 'restart: "no"', "restart: always", "restart_policy_missing"),
    ],
)
def test_adversarial_deployment_mutations_are_detected(
    artifact: str,
    old: str,
    new: str,
    expected: str,
) -> None:
    dockerfile = _text(DOCKERFILE)
    compose = _text(COMPOSE_FILE)
    selected = dockerfile if artifact == "dockerfile" else compose
    assert old in selected
    if artifact == "dockerfile":
        dockerfile = dockerfile.replace(old, new, 1)
    else:
        compose = compose.replace(old, new, 1)
    assert expected in _deployment_errors(dockerfile, compose)


def test_gate_schema_policy_and_benchmark_artifacts_are_parseable() -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas" / "aura_gate_authority_envelope.schema.json").read_text(encoding="utf-8")
    )
    policy = json.loads((REPO_ROOT / "examples" / "aura_gate_policy.json").read_text(encoding="utf-8"))
    benchmark = json.loads(
        (
            REPO_ROOT / "docs" / "evidence" / "AURA_GATE_PHASE2_AGENT_BRIDGE_COUNCIL_V3_BENCHMARK_2026-07-18.json"
        ).read_text(encoding="utf-8")
    )

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["human_review_required"] == {"const": True}
    assert schema["properties"]["automatic_promotion"] == {"const": False}
    assert policy["policy_id"].startswith("GATE-POLICY-sha256:")
    assert policy["private_only"] is True
    assert policy["production_mutation"] is False
    assert benchmark["full_codex_session_provider_telemetry"]["availability"] == "NOT_AVAILABLE"
    combined = benchmark["combined_non_overlapping_proxy"]
    assert combined["recorded_input_token_estimate"] == 37_907
    assert combined["recorded_output_token_estimate"] == 1_852
    assert combined["recorded_total_token_estimate"] == 39_759
    assert combined["estimated_tokens_saved"] == 51_987
    assert combined["estimated_percent_saved"] == 56.66
