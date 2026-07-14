from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"marker missing in {path}: {old[:160]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path: str, marker: str, block: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if block in text:
        return
    if marker not in text:
        raise RuntimeError(f"marker missing in {path}: {marker!r}")
    target.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")


def replace_between(path: str, start: str, end: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    left = text.find(start)
    right = text.find(end, left + len(start))
    if left < 0 or right < 0:
        raise RuntimeError(f"block markers missing in {path}")
    target.write_text(text[:left] + replacement + text[right:], encoding="utf-8")


def append_once(path: str, marker: str, block: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + block.strip() + "\n", encoding="utf-8")


def repair_fusion() -> None:
    replace_once("aura_adaptive_fusion.py", "import json\n", "import json\nimport math\n")
    insert_before(
        "aura_adaptive_fusion.py",
        "\n\nclass AdaptiveFusionPanelExecutor:",
        '''\n\ndef _schema_value_valid(value: Any, schema: Mapping[str, Any]) -> bool:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        required = schema.get("required", ())
        if any(field not in value for field in required):
            return False
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            return False
        return all(
            _schema_value_valid(item, properties[key])
            for key, item in value.items()
            if key in properties
        )
    if expected == "array":
        return isinstance(value, list) and all(
            _schema_value_valid(item, schema.get("items", {})) for item in value
        )
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return type(value) is bool
    if expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        number = float(value)
        if not math.isfinite(number):
            return False
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        return (minimum is None or number >= float(minimum)) and (
            maximum is None or number <= float(maximum)
        )
    return True
''',
    )
    replace_once(
        "aura_adaptive_fusion.py",
        '        schema = JUDGE_SCHEMA if role == "JUDGE" else PANEL_SCHEMA\n        return all(field in parsed for field in schema["required"])\n',
        '        schema = JUDGE_SCHEMA if role == "JUDGE" else PANEL_SCHEMA\n        return _schema_value_valid(parsed, schema)\n',
    )
    replace_once(
        "aura_adaptive_fusion.py",
        '''            packet = build_telemetry_packet(
                linkage=linkage,
                provider=str(kwargs.get("provider") or ""),
                model=str(kwargs.get("model") or ""),
                raw_usage={},
                timings=StageTimings(generation_ms=max(0.0, float(latency) * 1000.0)),
                pricing_registry=self.pricing_registry,
                policy_mode=PANEL,
                verifier_pass=passed,
                format_valid=passed,
                failure_class="" if passed else str(error or "FUSION_SCHEMA_REJECTED"),
                shadow_only=False,
                extra_evidence={
                    "fusion_agent": agent_name,
                    "fusion_role": role,
                    "used_response_schema": bool(used_schema),
                    "authorization_id": authorization.authorization_id,
                },
            )
            persistence = None
            if self.persist_telemetry:
                persistence = persist_telemetry_packet(
                    packet,
                    cognome_store=self.store,
                    empirical_ledger=self.empirical_ledger,
                    logger_sink=self.logger_sink,
                )
            with lock:
                links[agent_name] = {
                    "profile_id": profile_id,
                    "task_context_id": context.task_context_id,
                    "route_decision_id": live_decision.route_decision_id,
                    "call_id": linkage.call_id,
                    "observation_id": packet.observation.observation_id,
                    "cost_run_id": linkage.cost_run_id,
                    "persistence": persistence,
                }
''',
        '''            with lock:
                links[agent_name] = {
                    "profile_id": profile_id,
                    "task_context_id": context.task_context_id,
                    "route_decision_id": live_decision.route_decision_id,
                    "call_id": linkage.call_id,
                    "cost_run_id": linkage.cost_run_id,
                    "linkage": linkage,
                    "provider": str(kwargs.get("provider") or ""),
                    "model": str(kwargs.get("model") or ""),
                    "latency": max(0.0, float(latency)),
                    "verifier_pass": passed,
                    "failure_class": "" if passed else str(error or "FUSION_SCHEMA_REJECTED"),
                    "used_response_schema": bool(used_schema),
                }
''',
    )
    replace_once(
        "aura_adaptive_fusion.py",
        '''        result = coordinator.run(
            objective,
            mode="adaptive_panel",
            target_file=str(routing.get("primary_file") or "") or None,
            target_symbol=(list(routing.get("key_functions", []) or [None])[0]),
            extra_capsule={
                "task_context_id": context.task_context_id,
                "route_decision_id": live_decision.route_decision_id,
                "authorization_id": authorization.authorization_id,
                "capability_graph_digest": context.capability_graph_digest,
                "capability_path_digest": plan.get("path_resolution", {}).get("path_digest", ""),
            },
        ).to_dict()
        for output in result.get("panel_outputs", []):
''',
        '''        result = coordinator.run(
            objective,
            mode="adaptive_panel",
            target_file=str(routing.get("primary_file") or "") or None,
            target_symbol=(list(routing.get("key_functions", []) or [None])[0]),
            extra_capsule={
                "task_context_id": context.task_context_id,
                "route_decision_id": live_decision.route_decision_id,
                "authorization_id": authorization.authorization_id,
                "capability_graph_digest": context.capability_graph_digest,
                "capability_path_digest": plan.get("path_resolution", {}).get("path_digest", ""),
            },
        ).to_dict()
        persistence_failed = False
        for link in links.values():
            packet = build_telemetry_packet(
                linkage=link.pop("linkage"),
                provider=link.pop("provider"),
                model=link.pop("model"),
                raw_usage={},
                timings=StageTimings(generation_ms=link.pop("latency") * 1000.0),
                pricing_registry=self.pricing_registry,
                policy_mode=PANEL,
                verifier_pass=link["verifier_pass"],
                format_valid=link["verifier_pass"],
                failure_class=link.pop("failure_class"),
                shadow_only=False,
                extra_evidence={
                    "fusion_agent": next(
                        (name for name, candidate in links.items() if candidate is link), ""
                    ),
                    "used_response_schema": link.pop("used_response_schema"),
                    "authorization_id": authorization.authorization_id,
                },
            )
            link["observation_id"] = packet.observation.observation_id
            link["persistence"] = None
            if self.persist_telemetry:
                try:
                    link["persistence"] = persist_telemetry_packet(
                        packet,
                        cognome_store=self.store,
                        empirical_ledger=self.empirical_ledger,
                        logger_sink=self.logger_sink,
                    )
                except Exception as exc:
                    persistence_failed = True
                    link["persistence_error"] = f"TELEMETRY_PERSISTENCE_EXCEPTION:{type(exc).__name__}"
        for output in result.get("panel_outputs", []):
''',
    )
    replace_once(
        "aura_adaptive_fusion.py",
        '''        result["judge_output"] = judge_output
        result["calls"] = [links[name] | {"agent": name} for name in sorted(links)]
''',
        '''        result["judge_output"] = judge_output
        result["ok"] = (
            bool(result.get("ok"))
            and not persistence_failed
            and len(links) == len(profile_ids)
            and all(bool(item.get("verifier_pass")) for item in links.values())
        )
        result["calls"] = [links[name] | {"agent": name} for name in sorted(links)]
''',
    )
    replace_once(
        "aura_adaptive_fusion.py",
        '''        if len(profile_ids) < 3:
            raise ValueError("PANEL execution requires at least two panel profiles and one judge profile")
''',
        '''        if len(profile_ids) < 3:
            raise ValueError("PANEL execution requires at least two panel profiles and one judge profile")
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("PANEL execution cannot reuse the same profile")
''',
    )


def repair_model_router() -> None:
    insert_before(
        "aura_adaptive_model_router.py",
        "\n\ndef _forced_direct(",
        '''\n\ndef _candidate_set_digest(candidates: Sequence[Mapping[str, Any]]) -> str:
    normalized = [dict(item) for item in candidates]
    normalized.sort(key=lambda item: str(item.get("profile_id") or ""))
    return stable_digest(normalized)
''',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        "        self.executor_factory = executor_factory\n",
        "        self.executor_factory = executor_factory\n        self._used_authorization_ids: set[str] = set()\n",
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '''        fields = dict(task_fields or {})
        fields.setdefault("task_family", str(fields.get("domain") or "adaptive_route"))
''',
        '''        fields = dict(task_fields or {})
        fields.setdefault("task_family", str(fields.get("domain") or "adaptive_route"))
''',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '''        fields.setdefault("source_hash_digest", stable_digest(routing.get("source_hashes", {})))
        context = task_context_from_path(
''',
        '''        fields.setdefault("source_hash_digest", stable_digest(routing.get("source_hashes", {})))
        exact_required = (
            str(fields.get("action") or "").lower() == "patch"
            or str(fields.get("exactness_required") or "").upper().startswith("EXACT")
        )
        if exact_required and (
            routing.get("routing_source") != "dynamic_topology"
            or not routing.get("source_hashes")
        ):
            return {
                "status": DENIED,
                "executed": False,
                "execution_mode": SHADOW,
                "denial_reasons": ["exact topology and source hashes are required for this task"],
                "routing": routing,
                "capability_resolution": resolution,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                "version": ADAPTIVE_ROUTER_VERSION,
            }
        context = task_context_from_path(
''',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '''            if not matches:
                override_errors.append("forced model is not present in the graph-pinned candidate set")
            elif not matches[0].admitted:
''',
        '''            if not matches:
                override_errors.append("forced model is not present in the graph-pinned candidate set")
            elif len(matches) > 1:
                override_errors.append("forced model selector is ambiguous; use an exact profile ID or provider:model")
            elif not matches[0].admitted:
''',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '''        evidence_digest = stable_digest({
            "shadow": shadow.to_dict(),
            "forced_model": forced_model or "",
            "topology_digest": routing.get("topology_digest", ""),
            "path_digest": path_resolution.get("path_digest", ""),
        })
''',
        '''        candidate_evidence_digest = _candidate_set_digest(
            path_resolution.get("model_candidates", []) or []
        )
        evidence_digest = stable_digest({
            "shadow": shadow.to_dict(),
            "forced_model": forced_model or "",
            "topology_digest": routing.get("topology_digest", ""),
            "path_digest": path_resolution.get("path_digest", ""),
            "candidate_evidence_digest": candidate_evidence_digest,
        })
''',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '            "candidate_records": candidate_records,\n            "routing": routing,\n',
        '            "candidate_records": candidate_records,\n            "candidate_evidence_digest": candidate_evidence_digest,\n            "routing": routing,\n',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '                "capability_path_digest": path_resolution.get("path_digest", ""),\n                "topology_digest": routing.get("topology_digest", ""),\n',
        '                "capability_path_digest": path_resolution.get("path_digest", ""),\n                "candidate_evidence_digest": candidate_evidence_digest,\n                "topology_digest": routing.get("topology_digest", ""),\n',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '''        if current.get("graph_digest") != plan.get("path_resolution", {}).get("graph_digest"):
            errors.append("capability graph changed after route planning")
        for profile_id in plan.get("selected_option", {}).get("profile_ids", []) or []:
''',
        '''        if current.get("graph_digest") != plan.get("path_resolution", {}).get("graph_digest"):
            errors.append("capability graph changed after route planning")
        expected_evidence = str(
            plan.get("candidate_evidence_digest")
            or _candidate_set_digest(plan.get("path_resolution", {}).get("model_candidates", []) or [])
        )
        current_evidence = _candidate_set_digest(current.get("model_candidates", []) or [])
        if current_evidence != expected_evidence:
            errors.append("candidate evidence changed after route planning")
        for profile_id in plan.get("selected_option", {}).get("profile_ids", []) or []:
''',
    )
    replace_once(
        "aura_adaptive_model_router.py",
        '''        executor = factory(router=self)
        return executor.execute(objective, **kwargs)
''',
        '''        executor = factory(router=self)
        try:
            return executor.execute(objective, **kwargs)
        finally:
            if hasattr(executor, "close"):
                executor.close()
''',
    )


def repair_executor() -> None:
    insert_before(
        "aura_adaptive_model_executor.py",
        "\n\nclass AdaptiveModelExecutor:",
        '''\n\ndef paired_live_comparison_id(authorization_id: str) -> str:
    authorization = str(authorization_id or "").strip()
    if not authorization:
        raise ValueError("authorization_id must not be empty")
    return stable_id("paired-live", {"authorization_id": authorization})
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        "        self.now = now\n",
        "        self.now = now\n        self._closed = False\n",
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''    def close(self) -> None:
        if self._owns_ledger and self.empirical_ledger is not None and hasattr(self.empirical_ledger, "close"):
            self.empirical_ledger.close()
''',
        '''    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_ledger and self.empirical_ledger is not None and hasattr(self.empirical_ledger, "close"):
            self.empirical_ledger.close()
        if self.panel_executor is not None and hasattr(self.panel_executor, "close"):
            self.panel_executor.close()
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''            raw = (self.verifier or _default_verifier)(
                text,
                error,
                context=context,
                candidate=candidate,
                objective=objective,
            )
            if isinstance(raw, bool):
''',
        '''            try:
                raw = (self.verifier or _default_verifier)(
                    text,
                    error,
                    context=context,
                    candidate=candidate,
                    objective=objective,
                )
            except Exception as exc:
                result = {
                    "passed": False,
                    "format_valid": False,
                    "tests_passed": None,
                    "tests_failed": None,
                    "failure_class": f"VERIFIER_EXCEPTION:{type(exc).__name__}",
                }
                return result, max(0.0, (self.now() - started) * 1000.0)
            if isinstance(raw, bool):
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''        egress = self.egress_factory(
            provider=provider,
            model=model,
            task=call_type,
            aspect="adaptive_router",
        )
        started = self.now()
        raw = egress.generate(
            objective,
            router_context=router_context or None,
            call_type=call_type,
        )
        elapsed = max(0.0, self.now() - started)
''',
        '''        started = self.now()
        try:
            egress = self.egress_factory(
                provider=provider,
                model=model,
                task=call_type,
                aspect="adaptive_router",
            )
            raw = egress.generate(
                objective,
                router_context=router_context or None,
                call_type=call_type,
            )
        except Exception as exc:
            return {
                "text": None,
                "error": f"EGRESS_EXCEPTION:{type(exc).__name__}",
                "latency_sec": max(0.0, self.now() - started),
                "usage": {},
                "returned_model": model,
            }
        elapsed = max(0.0, self.now() - started)
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        "        estimated_calls = 0 if policy_mode == ZERO_MODEL else len(profile_ids) + (1 if policy_mode == PANEL else 0)\n",
        "        estimated_calls = 0 if policy_mode == ZERO_MODEL else len(profile_ids)\n",
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''        if policy_mode == ZERO_MODEL and self.deterministic_executor is None:
            errors.append("ZERO_MODEL live execution requires an injected deterministic executor")
''',
        '''        if str(context.risk or "LOW").upper() in _HIGH_RISK and policy_mode != PANEL and self.verifier is None:
            errors.append("high-risk DIRECT/CASCADE execution requires an explicit verifier")
        if policy_mode == ZERO_MODEL and self.deterministic_executor is None:
            errors.append("ZERO_MODEL live execution requires an injected deterministic executor")
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''        comparison_id = stable_id("paired-live", {
            "authorization_id": auth.authorization_id,
            "proposal_route_decision_id": plan["route_decision"]["route_decision_id"],
        })
''',
        '''        comparison_id = paired_live_comparison_id(auth.authorization_id)
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '            return self._deny(plan, ["experiment comparison ID mismatch"], auth.authorization_id)\n',
        '            return self._deny(plan, ["authorization has already been consumed or its comparison claim failed"], auth.authorization_id)\n',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''        fresh = evaluate_shadow_route(
            context=context,
            path_resolution=plan["path_resolution"],
            policy=self.router.policy,
            created_at=self.now(),
        )
        assessments = tuple(fresh.candidate_assessments)
''',
        '''        fresh = evaluate_shadow_route(
            context=context,
            path_resolution=plan["path_resolution"],
            policy=self.router.policy,
            created_at=self.now(),
        )
        assessments = tuple(fresh.candidate_assessments)
        assessment_by_profile = {item.candidate.profile_id: item for item in assessments}
        if any(
            profile_id not in assessment_by_profile
            or not assessment_by_profile[profile_id].admitted
            for profile_id in profile_ids
        ):
            return self._deny(plan, ["selected profile failed fresh admission"], auth.authorization_id)
        if not plan.get("forced_human_override"):
            fresh_option = fresh.selected_option
            if (
                fresh_option is None
                or fresh_option.policy_mode != policy_mode
                or tuple(fresh_option.profile_ids) != profile_ids
            ):
                return self._deny(plan, ["policy selection changed after route planning"], auth.authorization_id)
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''        if policy_mode == ZERO_MODEL:
            output = self.deterministic_executor(objective, context=context, routing=plan["routing"])
            return {**common, "status": "EXECUTED", "executed": True, "output": output, "calls": []}
        if policy_mode == PANEL:
            panel = self.panel_executor(
                objective=objective,
                plan=plan,
                context=context,
                live_decision=live_decision,
                authorization=auth,
                comparison_id=comparison_id,
                correlation_id=correlation_id,
            )
            return {
                **common,
                "status": "EXECUTED" if bool(panel.get("ok")) else "FAILED",
                "executed": True,
                "panel_result": panel,
            }
''',
        '''        if policy_mode == ZERO_MODEL:
            try:
                output = self.deterministic_executor(objective, context=context, routing=plan["routing"])
            except Exception as exc:
                return {
                    **common,
                    "status": "FAILED",
                    "executed": True,
                    "error": f"DETERMINISTIC_EXECUTOR_EXCEPTION:{type(exc).__name__}",
                    "calls": [],
                }
            return {**common, "status": "EXECUTED", "executed": True, "output": output, "calls": []}
        if policy_mode == PANEL:
            try:
                panel = self.panel_executor(
                    objective=objective,
                    plan=plan,
                    context=context,
                    live_decision=live_decision,
                    authorization=auth,
                    comparison_id=comparison_id,
                    correlation_id=correlation_id,
                )
            except Exception as exc:
                return {
                    **common,
                    "status": "FAILED",
                    "executed": True,
                    "error": f"PANEL_EXECUTOR_EXCEPTION:{type(exc).__name__}",
                }
            return {
                **common,
                "status": "EXECUTED" if panel.get("ok") is True else "FAILED",
                "executed": True,
                "panel_result": panel,
            }
''',
    )
    replace_once(
        "aura_adaptive_model_executor.py",
        '''            lineage = self._persist_call(
                context=context,
                decision=live_decision,
                candidate=candidate,
                result=call_result,
                verification=verification,
                verifier_ms=verifier_ms,
                correlation_id=correlation_id,
                attempt_index=index,
                fallback_index=index if policy_mode == CASCADE else 0,
                comparison_id=comparison_id,
            )
''',
        '''            try:
                lineage = self._persist_call(
                    context=context,
                    decision=live_decision,
                    candidate=candidate,
                    result=call_result,
                    verification=verification,
                    verifier_ms=verifier_ms,
                    correlation_id=correlation_id,
                    attempt_index=index,
                    fallback_index=index if policy_mode == CASCADE else 0,
                    comparison_id=comparison_id,
                )
            except Exception as exc:
                final_text = call_result.get("text")
                final_error = f"TELEMETRY_PERSISTENCE_EXCEPTION:{type(exc).__name__}"
                verified = False
                break
''',
    )


def repair_authorization_and_store() -> None:
    replace_once(
        "aura_model_cognome_execution_auth.py",
        '''        errors: list[str] = []
        if now < self.issued_at:
''',
        '''        errors: list[str] = []
        if not math.isfinite(float(now)):
            errors.append("authorization evaluation time must be finite")
            return errors
        if type(call_count) is not int or call_count < 0:
            errors.append("call_count must be a non-negative integer")
        if len(tuple(profile_ids)) != len(set(str(item) for item in profile_ids)):
            errors.append("selected profile IDs cannot contain duplicates")
        if now < self.issued_at:
''',
    )
    replace_once(
        "aura_model_cognome_store_io.py",
        '''        if mode == "PAIRED_LIVE" and not approved: raise ValueError("PAIRED_LIVE requires explicit approval")
        comparison_id = str(clean.get("comparison_id") or stable_id("comparison", clean)); payload = clean | {"comparison_id": comparison_id,"approved_live": approved}; encoded = json.dumps(payload,sort_keys=True,separators=(",",":"))
''',
        '''        if mode == "PAIRED_LIVE" and not approved: raise ValueError("PAIRED_LIVE requires explicit approval")
        if mode == "PAIRED_LIVE" and not str(clean.get("authorization_id") or "").strip(): raise ValueError("PAIRED_LIVE requires authorization_id")
        comparison_id = str(clean.get("comparison_id") or stable_id("comparison", clean)); payload = clean | {"comparison_id": comparison_id,"approved_live": approved}; encoded = json.dumps(payload,sort_keys=True,separators=(",",":"))
''',
    )


def repair_compat() -> None:
    replace_once(
        "aura_router_adaptive_compat.py",
        '''def load_authorization(value: Any) -> Any:
    if value is None or hasattr(value, "validate_for"):
        return value
    from aura_model_cognome_execution_auth import ExecutionAuthorization

    if isinstance(value, Mapping):
''',
        '''def load_authorization(value: Any) -> Any:
    from aura_model_cognome_execution_auth import ExecutionAuthorization

    if value is None or isinstance(value, ExecutionAuthorization):
        return value
    if isinstance(value, Mapping):
''',
    )
    replace_between(
        "aura_router_adaptive_compat.py",
        "def _router(\n",
        "def route_test_case(\n",
        '''def _router(
    auto_router: Any,
    *,
    verifier: Any,
    fusion_required: bool = False,
    mock: bool = False,
):
    from aura_adaptive_model_executor import AdaptiveModelExecutor
    from aura_adaptive_model_router import AdaptiveModelRouter
    from aura_shadow_model_router import ShadowRoutingPolicy

    policy = None
    if fusion_required:
        policy = ShadowRoutingPolicy(
            high_risk_direct_min_success=1.0,
            panel_uncertainty_threshold=0.0,
            panel_size=3,
            allow_panel=True,
        )

    def executor_factory(router: AdaptiveModelRouter):
        panel_executor = None
        if fusion_required:
            from aura_adaptive_fusion import AdaptiveFusionPanelExecutor

            panel_executor = AdaptiveFusionPanelExecutor(
                repo_root=auto_router.root,
                store=router.store,
                mock=mock,
            )
        return AdaptiveModelExecutor(
            router=router,
            verifier=verifier,
            panel_executor=panel_executor,
        )

    return AdaptiveModelRouter(
        repo_root=auto_router.root,
        policy=policy,
        executor_factory=executor_factory,
    )


''',
    )
    replace_once(
        "aura_router_adaptive_compat.py",
        '''    mode = resolve_mode(routing_mode)
    if mode == LEGACY:
''',
        '''    mode = resolve_mode(routing_mode)
    if type(data_egress_allowed) is not bool or type(mock) is not bool:
        raise ValueError("data_egress_allowed and mock must be booleans")
    if mode == LEGACY:
''',
    )
    # Same guard for the second public adaptive entry point.
    text = Path("aura_router_adaptive_compat.py").read_text(encoding="utf-8")
    first = text.find('    mode = resolve_mode(routing_mode)\n')
    second = text.find('    mode = resolve_mode(routing_mode)\n', first + 1)
    guard = (
        '    mode = resolve_mode(routing_mode)\n'
        '    if type(data_egress_allowed) is not bool or type(mock) is not bool:\n'
        '        raise ValueError("data_egress_allowed and mock must be booleans")\n'
    )
    if second >= 0 and not text.startswith(guard, second):
        text = text[:second] + guard + text[second + len('    mode = resolve_mode(routing_mode)\n'):]
        Path("aura_router_adaptive_compat.py").write_text(text, encoding="utf-8")


def repair_ai_router() -> None:
    replace_once(
        "aura_ai_router.py",
        "_INDEX_CACHE: dict[str, Any] | None = None\n_INDEX_CACHE_MTIME: float | None = None\n",
        "_INDEX_CACHE: dict[str, Any] | None = None\n_INDEX_CACHE_MTIME: float | None = None\n_INDEX_CACHE_PATH: str | None = None\n",
    )
    replace_once(
        "aura_ai_router.py",
        '''    global _INDEX_CACHE, _INDEX_CACHE_MTIME
    try:
        mtime = os.path.getmtime(path)
''',
        '''    global _INDEX_CACHE, _INDEX_CACHE_MTIME, _INDEX_CACHE_PATH
    cache_path = str(Path(path).resolve())
    try:
        mtime = os.path.getmtime(cache_path)
''',
    )
    replace_once(
        "aura_ai_router.py",
        "    if _INDEX_CACHE is not None and _INDEX_CACHE_MTIME == mtime:\n        return _INDEX_CACHE\n",
        "    if _INDEX_CACHE is not None and _INDEX_CACHE_MTIME == mtime and _INDEX_CACHE_PATH == cache_path:\n        return _INDEX_CACHE\n",
    )
    replace_once(
        "aura_ai_router.py",
        '        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()\n',
        '        lines = Path(cache_path).read_text(encoding="utf-8", errors="ignore").splitlines()\n',
    )
    replace_once("aura_ai_router.py", '        "source": path,\n', '        "source": cache_path,\n')
    replace_once(
        "aura_ai_router.py",
        "    _INDEX_CACHE_MTIME = mtime\n    return _INDEX_CACHE\n",
        "    _INDEX_CACHE_MTIME = mtime\n    _INDEX_CACHE_PATH = cache_path\n    return _INDEX_CACHE\n",
    )
    insert_before(
        "aura_ai_router.py",
        "\n\ndef _dynamic_route(",
        '''\n\ndef _exact_context_packet(anchor: Any, node: Any, radius: int = 1) -> Any:
    from aura_topological_context_anchor import CodeTopoContextPacket

    radius = max(0, min(3, int(radius)))
    visited = {node.node_id}
    neighbor_edge: dict[str, Any] = {}
    queue = [(node.node_id, 0)]
    while queue and len(visited) < 24:
        node_id, distance = queue.pop(0)
        if distance >= radius:
            continue
        for edge in [*anchor.outgoing.get(node_id, []), *anchor.incoming.get(node_id, [])]:
            other = edge.dst_id if edge.src_id == node_id else edge.src_id
            if other not in anchor.nodes or other in visited:
                continue
            visited.add(other)
            neighbor_edge[other] = edge
            queue.append((other, distance + 1))

    source_spans = []
    hashes: dict[str, str] = {}
    token_estimate = 0
    ordered_ids = [node.node_id, *sorted(visited - {node.node_id})]
    for node_id in ordered_ids:
        current = anchor.nodes[node_id]
        span = anchor._source_span_for_node(
            current, role="target" if node_id == node.node_id else "neighbor"
        )
        if span:
            source_spans.append(span)
            token_estimate += _estimate_tokens(str(span.get("source", "")))
        hashes[current.node_id] = current.source_hash
        hashes.setdefault(current.file_path, anchor.file_hashes.get(current.file_path, ""))

    neighbor_summaries = []
    for node_id in sorted(visited - {node.node_id}):
        current = anchor.nodes[node_id]
        edge = neighbor_edge.get(node_id)
        neighbor_summaries.append({
            "node_id": current.node_id,
            "file_path": current.file_path,
            "symbol": current.symbol,
            "kind": current.kind,
            "span": [current.start_line, current.end_line],
            "source_hash": current.source_hash,
            "edge_type": edge.edge_type if edge else "neighbor",
            "edge_evidence": edge.evidence if edge else "",
            "confidence": edge.confidence if edge else 1.0,
        })
    tests = anchor._tests_for_nodes([node.node_id])
    return CodeTopoContextPacket(
        target_nodes=[node],
        source_spans=source_spans,
        neighbor_summaries=neighbor_summaries[:16],
        tests=tests,
        hashes={key: value for key, value in hashes.items() if value},
        warnings=list(dict.fromkeys(anchor.warnings)),
        token_estimate=token_estimate,
        route_diagnostics={
            "route": "BUILDER_PATCH" if tests else "TEST_GAP_FILL",
            "reason": "exact_node_grounded" if tests else "exact_node_grounded_missing_tests",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        },
    )
''',
    )
    replace_once(
        "aura_ai_router.py",
        '''    candidate_symbols = list(dict.fromkeys([*requested_symbols, *resolved_symbols]))
    exact_nodes: list[Any] = []
    for symbol in candidate_symbols:
        lookup = anchor.lookup_symbol(symbol)
        exact_nodes.extend(lookup.exact_hits)
        if len(exact_nodes) >= 6:
            break
''',
        '''    candidate_symbols = list(dict.fromkeys([*requested_symbols, *resolved_symbols]))
    preferred_files = list(dict.fromkeys([*requested_files, *resolved_files]))
    preferred_rank = {_normalize_path(path): index for index, path in enumerate(preferred_files)}
    primary_requested = _normalize_path(requested_files[0]) if requested_files else ""
    selection_warnings: list[str] = []
    exact_nodes: list[Any] = []
    for symbol in candidate_symbols:
        lookup = anchor.lookup_symbol(symbol)
        hits = list(lookup.exact_hits)
        primary_hits = [node for node in hits if _normalize_path(node.file_path) == primary_requested]
        preferred_hits = [node for node in hits if _normalize_path(node.file_path) in preferred_rank]
        if primary_hits:
            hits = primary_hits
        elif len(preferred_hits) == 1:
            hits = preferred_hits
        elif len(preferred_hits) > 1 or len(hits) > 1:
            selection_warnings.append("ambiguous_exact_symbol_without_unique_file_target")
            continue
        hits.sort(key=lambda node: (preferred_rank.get(_normalize_path(node.file_path), 10**6), node.file_path, node.start_line))
        exact_nodes.extend(hits)
        if len(exact_nodes) >= 6:
            break
''',
    )
    replace_once(
        "aura_ai_router.py",
        '''    warnings: list[str] = []
    for node in exact_nodes[:4]:
        packet = anchor.nearest_context(node.symbol, radius=1)
''',
        '''    warnings: list[str] = list(selection_warnings)
    primary_packet = None
    for node in exact_nodes[:4]:
        packet = _exact_context_packet(anchor, node, radius=1)
        if primary_packet is None:
            primary_packet = packet
''',
    )
    replace_once(
        "aura_ai_router.py",
        '''        caller_result = anchor.callers_of(node.symbol)
        callers.extend(
            _node_summary(item, confidence=score, relationship="caller")
            for item, score in caller_result.ranked_neighbors
        )
        callee_result = anchor.callees_of(node.symbol)
        callees.extend(
            _node_summary(item, confidence=score, relationship="callee")
            for item, score in callee_result.ranked_neighbors
        )
''',
        '''        callers.extend(
            _node_summary(anchor.nodes[edge.src_id], confidence=edge.confidence, relationship="caller")
            for edge in anchor.incoming.get(node.node_id, [])
            if edge.edge_type == "call" and edge.src_id in anchor.nodes
        )
        callees.extend(
            _node_summary(anchor.nodes[edge.dst_id], confidence=edge.confidence, relationship="callee")
            for edge in anchor.outgoing.get(node.node_id, [])
            if edge.edge_type == "call" and edge.dst_id in anchor.nodes
        )
''',
    )
    replace_once(
        "aura_ai_router.py",
        '''    if exact_nodes:
        nearest = anchor.nearest_context(exact_nodes[0].symbol, radius=1)
        router_context = _bounded_text(render_builder_context(nearest), token_budget)
''',
        '''    if exact_nodes and primary_packet is not None:
        router_context = _bounded_text(render_builder_context(primary_packet), token_budget)
''',
    )
    replace_once(
        "aura_ai_router.py",
        '''    primary_file = exact_nodes[0].file_path if exact_nodes else (
        resolved_files[0] if resolved_files else (requested_files[0] if requested_files else "")
    )
''',
        '''    primary_file = exact_nodes[0].file_path if exact_nodes else (
        requested_files[0] if requested_files else (resolved_files[0] if resolved_files else "")
    )
''',
    )
    replace_once(
        "aura_ai_router.py",
        '''        global _INDEX_CACHE, _INDEX_CACHE_MTIME
        _INDEX_CACHE = None
        _INDEX_CACHE_MTIME = None
''',
        '''        global _INDEX_CACHE, _INDEX_CACHE_MTIME, _INDEX_CACHE_PATH
        _INDEX_CACHE = None
        _INDEX_CACHE_MTIME = None
        _INDEX_CACHE_PATH = None
''',
    )


def repair_tests() -> None:
    append_once(
        "tests/test_aura_ai_router_dynamic.py",
        "test_query_router_prefers_explicit_file_for_duplicate_symbol",
        '''
def test_query_router_prefers_explicit_file_for_duplicate_symbol(tmp_path: Path) -> None:
    (tmp_path / "alpha.py").write_text("def target():\n    return 'alpha'\n", encoding="utf-8")
    (tmp_path / "beta.py").write_text("def target():\n    return 'beta'\n", encoding="utf-8")

    result = query_router(
        "change target in beta.py",
        repo_root=tmp_path,
        target_files=["beta.py"],
        target_symbols=["target"],
        static_fallback=False,
        resolver=_resolution,
    )

    assert result["primary_file"] == "beta.py"
    assert result["exact_symbols"][0]["file"] == "beta.py"
    assert "return 'beta'" in result["router_context"]
    assert "return 'alpha'" not in result["router_context"]
''',
    )
    append_once(
        "tests/test_aura_adaptive_security.py",
        "test_paired_live_comparison_id_is_authorization_bound",
        '''
def test_paired_live_comparison_id_is_authorization_bound() -> None:
    from aura_adaptive_model_executor import paired_live_comparison_id

    first = paired_live_comparison_id("authorization-a")
    second = paired_live_comparison_id("authorization-a")
    different = paired_live_comparison_id("authorization-b")
    assert first == second
    assert first != different
''',
    )
    append_once(
        "tests/test_aura_adaptive_fusion_schema.py",
        "test_fusion_schema_rejects_additional_properties_and_nonfinite_numbers",
        '''
def test_fusion_schema_rejects_additional_properties_and_nonfinite_numbers() -> None:
    import json

    extra = {
        "role": "THINKER", "answer": "x", "claims": [], "risks": [],
        "missing_info": [], "recommended_action": "review", "confidence": 0.5,
        "unexpected": True,
    }
    nonfinite = dict(extra)
    nonfinite.pop("unexpected")
    nonfinite["confidence"] = float("nan")
    assert AdaptiveFusionPanelExecutor._schema_passed("THINKER", json.dumps(extra), None) is False
    assert AdaptiveFusionPanelExecutor._schema_passed("THINKER", json.dumps(nonfinite), None) is False
''',
    )


def main() -> None:
    repair_fusion()
    repair_model_router()
    repair_executor()
    repair_authorization_and_store()
    repair_compat()
    repair_ai_router()
    repair_tests()


if __name__ == "__main__":
    main()
