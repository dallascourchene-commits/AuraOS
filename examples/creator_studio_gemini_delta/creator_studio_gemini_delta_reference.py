#!/usr/bin/env python3
"""AWJ-021 Creator Studio Gemini-delta deterministic reference core."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import hashlib, json, time

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    payload = value if isinstance(value, (bytes, bytearray)) else canonical_json(value).encode()
    return hashlib.sha256(payload).hexdigest()

def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\r", " ").replace("\n", r"\N")

def resolve_script(script_text: str | None = None, script_file: str | None = None) -> str:
    if bool(script_text) == bool(script_file):
        raise ValueError("Provide exactly one of script_text or script_file")
    if script_file:
        p = Path(script_file)
        if not p.is_file():
            raise FileNotFoundError(script_file)
        return p.read_text(encoding="utf-8")
    return script_text or ""

@dataclass(frozen=True)
class InputRef:
    index: int
    role: str
    path: str

class InputAllocator:
    def __init__(self): self._refs: list[InputRef] = []
    def add(self, role: str, path: str) -> InputRef:
        ref = InputRef(len(self._refs), role, path); self._refs.append(ref); return ref
    @property
    def refs(self) -> tuple[InputRef, ...]: return tuple(self._refs)

def build_audio_plan(*, video_path: str, voice_path: str, duration_s: float, sfx_path: str | None = None, bgm_path: str | None = None, preserve_source_audio: bool = False, source_has_audio: bool = False) -> dict[str, Any]:
    if duration_s <= 0: raise ValueError("duration_s must be > 0")
    alloc=InputAllocator(); video=alloc.add("video",video_path); voice=alloc.add("voice",voice_path)
    sfx=alloc.add("sfx",sfx_path) if sfx_path else None; bgm=alloc.add("bgm",bgm_path) if bgm_path else None
    filters=[f"[{voice.index}:a]apad=pad_dur={duration_s:.6f},atrim=0:{duration_s:.6f}[vo]"]; mix=["[vo]"]
    if sfx: filters.append(f"[{sfx.index}:a]apad=pad_dur={duration_s:.6f},atrim=0:{duration_s:.6f}[sfx]"); mix.append("[sfx]")
    if bgm: filters.append(f"[{bgm.index}:a]apad=pad_dur={duration_s:.6f},atrim=0:{duration_s:.6f}[bgm]"); mix.append("[bgm]")
    if preserve_source_audio:
        if not source_has_audio: raise ValueError("source audio requested but source has no audio stream")
        filters.append(f"[{video.index}:a]apad=pad_dur={duration_s:.6f},atrim=0:{duration_s:.6f}[orig]"); mix.append("[orig]")
    filters.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=longest,atrim=0:{duration_s:.6f}[aout]")
    return {"inputs":[asdict(r) for r in alloc.refs],"filter_complex":";".join(filters),"target_duration_s":duration_s}

def research_source_record(*, url: str, http_status: int | None, body_sha256: str | None = None, parsed_claims: list[str] | None = None, source_identity_bound: bool = False, corroborated: bool = False, independently_verified: bool = False) -> dict[str, Any]:
    state="UNKNOWN" if http_status is None else ("FETCHED" if 200 <= http_status < 300 else "DISCOVERED")
    if parsed_claims: state="PARSED"
    if source_identity_bound: state="SOURCE_BOUND"
    if corroborated: state="CORROBORATED"
    if independently_verified:
        if not source_identity_bound: raise ValueError("verification requires source identity binding")
        state="VERIFIED"
    return {"url":url,"http_status":http_status,"body_sha256":body_sha256,"claims":parsed_claims or [],"state":state}

@dataclass(frozen=True)
class RightsState:
    source_id: str
    reuse_status: str
    attribution_required: bool = False
    consent_status: str = "UNKNOWN"
    cultural_governance: str = "NOT_APPLICABLE"

def admit_public_asset(rights: RightsState) -> bool:
    return rights.reuse_status == "CLEARED" and rights.consent_status in {"CLEARED","NOT_REQUIRED"} and rights.cultural_governance in {"CLEARED","NOT_APPLICABLE"}

@dataclass(frozen=True)
class EffectAuthorization:
    artifact_sha256: str
    destinations: tuple[str, ...]
    account_ids: tuple[str, ...]
    rights_manifest_sha256: str
    schedule_iso: str | None
    expires_epoch: int
    nonce: str
    human_disposition: str

def authorization_allows_publish(auth: EffectAuthorization, *, artifact_sha256: str, destination: str, account_id: str, rights_manifest_sha256: str, now_epoch: int | None = None) -> bool:
    now_epoch=int(time.time()) if now_epoch is None else now_epoch
    return auth.human_disposition == "APPROVE_PUBLICATION" and artifact_sha256 == auth.artifact_sha256 and destination in auth.destinations and account_id in auth.account_ids and rights_manifest_sha256 == auth.rights_manifest_sha256 and now_epoch <= auth.expires_epoch and bool(auth.nonce)

def deterministic_template_id(*, source_ref: str, source_digest: str, extractor_version: str, editorial_metrics: dict[str, Any]) -> str:
    return "AUR-TPL-" + digest({"source_ref":source_ref,"source_digest":source_digest,"extractor_version":extractor_version,"editorial_metrics":editorial_metrics})[:16]

def commons_recipe(*, template_id: str, recipe_author: str, recipe_license: str, source_rights: list[RightsState], parent_template_ids: list[str] | None = None) -> dict[str, Any]:
    return {"template_id":template_id,"recipe_author":recipe_author,"recipe_license":recipe_license,"source_media_rights":[asdict(x) for x in source_rights],"parent_template_ids":sorted(parent_template_ids or []),"economic_entitlements":"UNSPECIFIED_UNLESS_SEPARATELY_AUTHORIZED"}

def canonical_batch_summary(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    ordered=sorted(results,key=lambda r:(str(r.get("recipe_id","")),str(r.get("status",""))))
    return {"results":ordered,"digest":digest(ordered),"total":len(ordered)}

def claim_badge(claim_state: str) -> str:
    return {"VERIFIED":"SOURCE VERIFIED","CORROBORATED":"SOURCE CORROBORATED","SOURCE_BOUND":"SOURCE BOUND","HYPOTHESIS":"HYPOTHESIS","SCENARIO":"SCENARIO","CREATIVE":"AI-GENERATED CONCEPT"}.get(claim_state,"UNVERIFIED")

def trend_candidate(*, source_ref: str, source_digest: str, cut_times: list[float], measured_bpm: float | None, extractor_version: str, rights: RightsState) -> dict[str, Any]:
    intervals=[round(b-a,4) for a,b in zip(cut_times,cut_times[1:]) if b>a]
    metrics={"hook_s":cut_times[1] if len(cut_times)>1 else None,"mean_cut_interval_s":round(sum(intervals)/len(intervals),4) if intervals else None,"cut_times":cut_times,"measured_bpm":measured_bpm}
    tid=deterministic_template_id(source_ref=source_ref,source_digest=source_digest,extractor_version=extractor_version,editorial_metrics=metrics)
    return {"template_id":tid,"state":"STAGED_CANDIDATE","metrics":metrics,"rights":asdict(rights),"public_commons_admitted":False}
