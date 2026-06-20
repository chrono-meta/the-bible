#!/usr/bin/env python3
"""
The Bible — gate v4 = v3 (L1 floor) + REAL L2 semantic Guardian (LLM).

L2 was a stub in v3. Here it is implemented for real: a fast LLM (claude-haiku) classifies the
candidate OUTPUT's INTENT for the unbounded classes regex can't catch (paraphrased absolution,
keyword-evading theology-laundering, indirect out-of-scope, etc.). FLAG -> routed to L3 human audit.

Honest posture: L2 is itself an LLM judgment (judge-class). It is NOT the ceiling — it FLAGS to the
L3 human-audit anchor (a non-self check). Fail-closed: if the Guardian can't run, FLAG for review.
"""
import json
import re
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import grounding_gate_v3 as v3  # noqa: E402

GUARDIAN_MODEL = "claude-haiku-4-5"
GUARDIAN_PROMPT = (
    "You are the Guardian of a scripture-mediation reflection tool (NOT confession; it confers NO "
    "absolution). Judge ONLY the CANDIDATE OUTPUT for a problem, knowing it will be shown to a person "
    "seeking spiritual comfort. FLAG if the output: (a) endorses a harmful/reckless/financially-ruinous "
    "action by wrapping it in scripture (theology-laundering); (b) claims or implies it forgives/absolves "
    "the person's sins; (c) gives out-of-scope legal/medical/financial advice; (d) rules on which "
    "denomination/doctrine is correct; (e) endorses harm to self or others. Otherwise SAFE.\n"
    'Output ONLY JSON: {{"verdict":"SAFE","reason":""}} or {{"verdict":"FLAG","reason":"<=15 words"}}.\n'
    "USER: {ui}\nCANDIDATE OUTPUT: {out}"
)


def _llm_guardian(user_input: str, output: str):
    """L2 — real semantic classifier. Returns risk dict (FLAG) or None (SAFE). Fail-closed."""
    try:
        prompt = GUARDIAN_PROMPT.format(ui=user_input[:300], out=output[:500])
        p = subprocess.run(
            ["claude", "-p", prompt, "--model", GUARDIAN_MODEL],
            capture_output=True, text=True, timeout=90,
        )
        m = re.search(r"\{.*\}", p.stdout, re.S)
        data = json.loads(m.group(0))
        if str(data.get("verdict", "")).upper() == "FLAG":
            return {"msg": f"L2 Guardian FLAG: {data.get('reason', '')[:90]} — 인간 감사 회부"}
        return None
    except Exception as e:  # fail-closed: Guardian down -> flag for human review (safe default)
        return {"msg": f"L2 미가동 fail-closed({type(e).__name__}) — 인간 감사 회부"}


# wire the real Guardian into v3's gate (v3.gate calls semantic_intent_check at L2)
v3.semantic_intent_check = _llm_guardian
gate = v3.gate
