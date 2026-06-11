"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit / Adaptive Communication)
DEPENDENCIES: argparse, json, os, re, time, aura_substrate, aura_llm_egress, aura_pricing
FUNCTIONS: CommProfile, ConversationLog, parse_feedback, interpret_reply, Conversationalist
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura Conversation — uniform polysynthetic chat that learns over time.
====================================================================

Conversation uses the SAME substrate packet as code tasks: your input is
compressed into a polysynthetic packet (+ guardrails incl. CONVERSE.md +
optional context), sent to the external LLM, which replies in the compact
[REPLY] envelope. Aura interprets/renders it for you.

It learns:
  * CommProfile         — persistent preference profile (verbosity, format,
                          liked-style exemplars, things to avoid) plus a
                          DKT-style mastery score that rises as you need fewer
                          corrections.
  * parse_feedback()    — turns your natural corrections ("say it shorter",
                          "I don't understand", "say more like X") into profile
                          updates, so replies adapt to you.
  * ConversationLog     — every turn logged polysynthetically with a timestamp
                          (Aura_Memory/aura_conversations.jsonl) to help her
                          learn faster (and feed crystallization/DKT).

The substrate stays LLM-free; the model is touched only at the egress.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time

from aura_substrate import AuraSubstrate, estimate_tokens, sanitize_code
from aura_llm_egress import ExternalLLM, usable_providers

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Aura_Memory")
CONVO_LOG_PATH = os.path.join(MEMORY_DIR, "aura_conversations.jsonl")
PROFILE_PATH = os.path.join(MEMORY_DIR, "aura_comm_profile.json")
EXEC_LOG_PATH = os.path.join(MEMORY_DIR, "aura_executions.jsonl")

_VERBOSITY = ("terse", "normal", "detailed")


# --------------------------------------------------------------------------- #
# Learning: preference profile + DKT mastery
# --------------------------------------------------------------------------- #

class CommProfile:
    """Persistent, learnable communication preferences for one operator."""

    def __init__(self, path: str = PROFILE_PATH):
        self.path = path
        self.data = self._load()

    def _default(self) -> dict:
        return {"verbosity": "normal", "format": "plain",
                "style_refs": [], "avoid": [],
                "turns": 0, "corrections": 0,
                "dkt_mastery": 0.30,   # 0..1 confidence she communicates well with this user
                "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return {**self._default(), **json.load(f)}
            except Exception:  # noqa: BLE001
                pass
        return self._default()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def packet_tags(self) -> list[str]:
        tags = [f"VERBOSITY:{self.data['verbosity'].upper()}",
                f"FORMAT:{self.data['format'].upper()}"]
        if self.data["style_refs"]:
            tags.append(f'STYLE_REF:"{self.data["style_refs"][-1]}"')
        if self.data["avoid"]:
            tags.append(f'AVOID:"{self.data["avoid"][-1]}"')
        return tags

    def reward(self, accepted: bool) -> None:
        """DKT update: EWMA toward mastery on accepted turns, dip on corrections."""
        self.data["turns"] += 1
        m = self.data["dkt_mastery"]
        if accepted:
            self.data["dkt_mastery"] = round(m + 0.10 * (1.0 - m), 4)
        else:
            self.data["corrections"] += 1
            self.data["dkt_mastery"] = round(max(0.0, m - 0.15 * m), 4)

    def apply_feedback(self, deltas: dict) -> None:
        if deltas.get("verbosity") in _VERBOSITY:
            self.data["verbosity"] = deltas["verbosity"]
        if deltas.get("format") in ("plain", "structured"):
            self.data["format"] = deltas["format"]
        for ex in deltas.get("style_refs", []):
            if ex and ex not in self.data["style_refs"]:
                self.data["style_refs"].append(ex)
                self.data["style_refs"] = self.data["style_refs"][-5:]
        for av in deltas.get("avoid", []):
            if av and av not in self.data["avoid"]:
                self.data["avoid"].append(av)
                self.data["avoid"] = self.data["avoid"][-5:]


_FEEDBACK_RULES = [
    (r"\b(shorter|concise|less|too long|tl;dr|brief)\b", {"verbosity": "terse"}),
    (r"\b(more detail|explain more|elaborate|say more|expand|in depth)\b", {"verbosity": "detailed"}),
    (r"\b(don'?t understand|confus|simpler|plain english|eli5|too complex)\b",
     {"verbosity": "terse", "format": "plain"}),
    (r"\b(bullet|list|steps|structured)\b", {"format": "structured"}),
    (r"\b(prose|paragraph|no bullets)\b", {"format": "plain"}),
]


def parse_feedback(text: str) -> dict:
    """Turn a natural correction into deterministic profile deltas."""
    low = (text or "").lower()
    deltas: dict = {"style_refs": [], "avoid": []}
    for pat, d in _FEEDBACK_RULES:
        if re.search(pat, low):
            deltas.update({k: v for k, v in d.items() if k not in ("style_refs", "avoid")})
    # "say it more like: X" / "like this: X"  -> liked exemplar
    m = re.search(r"(?:like this|more like|say it like)\s*[:\-]?\s*(.+)", text or "", re.I)
    if m:
        deltas["style_refs"].append(m.group(1).strip()[:160])
    # "don't say X" / "avoid X"
    m = re.search(r"(?:don'?t say|avoid|stop saying)\s*[:\-]?\s*(.+)", text or "", re.I)
    if m:
        deltas["avoid"].append(m.group(1).strip()[:160])
    return deltas


def is_feedback(text: str) -> bool:
    d = parse_feedback(text)
    return bool(d.get("verbosity") or d.get("format") or d["style_refs"] or d["avoid"])


# --------------------------------------------------------------------------- #
# Reply interpretation
# --------------------------------------------------------------------------- #

_REPLY_FIELD = re.compile(r"^([A-Z_]+):\s*(.*)$")


def interpret_reply(raw: str, mode: str = "expand") -> dict:
    """Parse the [REPLY] envelope; render it for the human (or pass shorthand)."""
    raw = sanitize_code(raw or "")[0]
    m = re.search(r"\[REPLY\](.*?)\[/REPLY\]", raw, re.DOTALL)
    body = m.group(1).strip() if m else raw.strip()
    fields: dict[str, str] = {}
    for line in body.splitlines():
        fm = _REPLY_FIELD.match(line.strip())
        if fm:
            fields[fm.group(1)] = fm.group(2).strip()
    if mode == "shorthand" or not fields:
        return {"fields": fields, "rendered": (m.group(0) if m else raw).strip()}
    parts = []
    if fields.get("ANSWER"):
        parts.append(fields["ANSWER"])
    if fields.get("DETAIL") and fields["DETAIL"].lower() not in ("none", ""):
        parts.append(fields["DETAIL"])
    if fields.get("NEXT") and fields["NEXT"].lower() not in ("none", ""):
        parts.append(f"(next: {fields['NEXT']})")
    rendered = "\n".join(parts) if parts else body
    return {"fields": fields, "rendered": rendered}


# --------------------------------------------------------------------------- #
# Conversation log (polysynthetic, timestamped)
# --------------------------------------------------------------------------- #

class ConversationLog:
    def __init__(self, path: str = CONVO_LOG_PATH):
        self.path = path

    def append(self, record: dict) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return out


# --------------------------------------------------------------------------- #
# Conversationalist
# --------------------------------------------------------------------------- #

class Conversationalist:
    def __init__(self, egress_factory=None, profile: CommProfile | None = None,
                 convo_log: ConversationLog | None = None, root: str | None = None,
                 exec_log=None):
        self.substrate = AuraSubstrate(root) if root else AuraSubstrate()
        self.egress_factory = egress_factory or (lambda p: ExternalLLM(provider=p))
        self.profile = profile or CommProfile()
        self.convo = convo_log or ConversationLog()
        if exec_log is not None:
            self.exec_log = exec_log
        else:
            try:
                from aura_router import ExecutionLog
                self.exec_log = ExecutionLog(EXEC_LOG_PATH)
            except Exception:  # noqa: BLE001
                self.exec_log = None

    def _pick_provider(self, forced: str | None) -> str | None:
        if forced:
            return forced
        pool = usable_providers(prefer_working=True)
        return pool[0] if pool else None

    def converse(self, user_input: str, forced_model: str | None = None,
                 mock: bool = False, display: str = "expand") -> dict:
        """Compress input -> LLM -> interpret reply; log + learn."""
        provider = "mock" if mock else self._pick_provider(forced_model)
        if provider is None:
            return {"ok": False, "reason": "no usable provider (add a key or use --mock)"}

        tags = ["ENV:CHAT", "OP:CONVERSE", "OUTPUT:POLY_REPLY"] + self.profile.packet_tags()
        pkg = self.substrate.compile(user_input, explicit_tags=tags, style="bracket")
        # uniform packet + base guardrails + the conversation protocol
        from aura_substrate import load_guardrails
        prompt = pkg.prompt.replace(pkg.guardrails, load_guardrails(extra_files=["CONVERSE.md"]))
        ain = estimate_tokens(prompt)

        try:
            egress = self.egress_factory(provider)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "reason": str(exc)}
        text, err, lat = egress.generate(prompt, max_tokens=500)
        if err or not text:
            return {"ok": False, "reason": err or "empty reply"}

        interp = interpret_reply(text, mode=display)
        aout = estimate_tokens(text)
        raw_in = estimate_tokens(
            "You are a helpful assistant. Answer the user fully.\n\nUser: " + user_input)

        turn = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user_input": user_input,
            "packet": pkg.packet,
            "style": "bracket",
            "verbosity": self.profile.data["verbosity"],
            "provider": egress.provider, "model": egress.model,
            "reply_raw": text, "reply_rendered": interp["rendered"],
            "aura_input_tokens": ain, "aura_output_tokens": aout,
            "raw_input_tokens": raw_in,
            "dkt_mastery": self.profile.data["dkt_mastery"],
            "feedback": None,
        }
        self.convo.append(turn)
        if self.exec_log:
            self.exec_log.append({
                "ts": turn["ts"], "task": "converse", "task_type": "converse",
                "aspect": "conversation", "chosen_provider": egress.provider,
                "model": egress.model, "style": "bracket", "output_mode": "poly_reply",
                "aura_input_tokens": ain, "aura_output_tokens": aout,
                "aura_total_cost_usd": egress.cost(ain, aout),
                "raw_input_tokens": raw_in,
                "est_raw_output_tokens": None, "est_raw_total_cost_usd": None,
            })
        # No correction yet -> provisionally reward (revised if user corrects next turn)
        self.profile.reward(accepted=True)
        self.profile.save()
        return {"ok": True, "rendered": interp["rendered"], "fields": interp["fields"],
                "raw": text, "packet": pkg.packet, "provider": egress.provider,
                "tokens": {"in": ain, "out": aout}, "latency_sec": round(lat, 3),
                "dkt_mastery": self.profile.data["dkt_mastery"]}

    def give_feedback(self, feedback_text: str) -> dict:
        """Apply a natural correction to the last turn -> learn."""
        deltas = parse_feedback(feedback_text)
        self.profile.apply_feedback(deltas)
        # the prior turn needed a correction -> DKT dip
        self.profile.reward(accepted=False)
        self.profile.save()
        turns = self.convo.read_all()
        if turns:
            turns[-1]["feedback"] = feedback_text
            # rewrite last line annotation by appending a feedback record
            self.convo.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "feedback_for_prev": feedback_text, "deltas": deltas})
        return {"ok": True, "profile": self.profile.data}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aura conversation (uniform polysynthetic, learns)")
    p.add_argument("--say", help="user input to converse about")
    p.add_argument("--feedback", help="natural correction applied to the last turn")
    p.add_argument("--model", default=None)
    p.add_argument("--display", default="expand", choices=["expand", "shorthand"])
    p.add_argument("--mock", action="store_true")
    p.add_argument("--profile", action="store_true", help="print the learned profile")
    args = p.parse_args(argv)

    c = Conversationalist()
    if args.profile:
        print(json.dumps(c.profile.data, indent=2))
        return 0
    if args.feedback:
        r = c.give_feedback(args.feedback)
        print(f"[+] learned. profile now: verbosity={r['profile']['verbosity']} "
              f"format={r['profile']['format']} mastery={r['profile']['dkt_mastery']}")
        return 0
    if not args.say:
        p.print_help()
        return 0
    res = c.converse(args.say, forced_model=args.model, mock=args.mock, display=args.display)
    if not res["ok"]:
        print(f"[-] {res['reason']}")
        return 1
    print(f"[Aura -> {res['provider']}] (in/out tokens {res['tokens']['in']}/{res['tokens']['out']}, "
          f"mastery {res['dkt_mastery']})\n")
    print(res["rendered"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
