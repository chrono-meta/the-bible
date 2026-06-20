#!/usr/bin/env python3
"""
The Bible — gate v3 (HARDENED from Round-2 battery + application-harm residual work).

Round-2 proved v2's regex gates are BRITTLE: evadable by whitespace-obfuscation, paraphrase,
keyword-avoidance, and prone to over-trigger (복수초). v3's honest response is 3-layered:

  (L1) MECHANICAL FLOOR  — normalization (strip-space, obfuscation-resistant) + patched patterns
                           + over-trigger fix (복수 negative lookahead). Closes the *cheap* classes.
                           HONEST: patching specific evasions is whack-a-mole; a NEW paraphrase re-evades.
  (L2) SEMANTIC INTENT   — `semantic_intent_check()` HOOK where the LLM-Guardian plugs in for
                           paraphrase/intent regex can't catch. (Stub here — no model call in the proto.)
  (L3) HUMAN-AUDIT ANCHOR — FLAGGED/borderline -> privacy-safe sample review queue. The NON-SELF anchor:
                           an LLM judging an LLM is self-referential (judge-only); the genuine ceiling for
                           application-harm + semantic evasion is human review. (the judge-robustness principle: an automated judge alone is foolable;
                           the irreducible ceiling is human review — named, not hidden.)

The application-harm (theology-laundering) residual is NOT closed mechanically — it is FLAGGED (L1
heuristic) + routed to L3 human audit. Honestly partial, by construction.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from grounding_gate import scripture_grounded, CRISIS_RESPONSE  # noqa: E402
from grounding_gate_v2 import (  # noqa: E402
    SELF_HARM, HARM_OTHERS, CONFIDENTIAL_REQ, CONFIDENTIAL_LEAK,
    ABSOLUTION, OUT_OF_SCOPE, ADJUDICATION, RISKY_ACTION,
)

# --- L1 patched pattern sets (brittle floor — explicitly whack-a-mole over Round-2 finds) ---
SELF_HARM_3 = SELF_HARM + [r"disappear\s*forever", r"nothing\s*matters", r"사라져\s*버리"]
ABSOLUTION_3 = ABSOLUTION + [r"깨끗합니다", r"씻겼", r"잘못\s*없", r"자유롭", r"clean\s*now", r"무죄"]
CONFIDENTIAL_REQ_3 = CONFIDENTIAL_REQ + [r"사람들이.*고백", r"주로.*고백", r"이번\s*주.*고백", r"다들.*고백"]
RISKY_ACTION_3 = RISKY_ACTION + [r"다\s*걸고", r"베팅", r"올인", r"한\s*번에.*걸", r"전\s*재산.*걸"]
# over-trigger fix: 복수 (revenge) but NOT 복수초(flower)/복수형(plural)/복수판/복수절
HARM_OTHERS_3 = [p for p in HARM_OTHERS if p != r"복수"] + [r"복수(?!초|형|판|절)"]


def _strip(t: str) -> str:
    return re.sub(r"\s+", "", t)


def _match(patterns, text: str) -> bool:
    """Match against original AND whitespace-stripped text (closes obfuscation like '죽 고 싶')."""
    s = _strip(text)
    return any(re.search(p, text, re.I) or re.search(p, s, re.I) for p in patterns)


def semantic_intent_check(user_input: str, output: str):
    """L2 HOOK — LLM-Guardian semantic classifier plugs in here for paraphrase/intent the
    regex floor cannot catch (the unbounded class). STUB (no model call). Returns a risk dict or None.
    In deployment: the Guardian agent; its verdict is JUDGED -> must be anchored by L3 human audit
    (an LLM judging an LLM is self-referential)."""
    return None


AUDIT_QUEUE = []  # L3 — FLAGGED/borderline -> privacy-safe human review (the non-self anchor / ceiling)


def _audit(reason, user_input, output):
    AUDIT_QUEUE.append({"reason": reason, "input": user_input[:60], "output": output[:60]})


def gate(user_input: str, candidate_output: str, citations: list) -> dict:
    # L1 SAFETY (normalized, obfuscation-resistant)
    if _match(SELF_HARM_3, user_input):
        return {"verdict": "CRISIS_OVERRIDE", "output": CRISIS_RESPONSE,
                "actions": ["escalate_to_human", "preserve_record"], "note": "self-harm (normalized)"}
    if _match(HARM_OTHERS_3, user_input):
        return {"verdict": "CRISIS_OVERRIDE",
                "output": "누군가를 해하려는 길로는 함께 갈 수 없습니다. 안전을 먼저 살피세요.",
                "actions": ["de-escalate", "no_endorsement"], "note": "harm-to-others"}
    # L1 CONFIDENTIALITY
    if _match(CONFIDENTIAL_REQ_3, user_input) or _match(CONFIDENTIAL_LEAK, candidate_output):
        return {"verdict": "REFUSED", "output": "다른 분이 나눈 내용은 전하지 않습니다. (격리·비공유)",
                "note": "confidentiality (incl. aggregation)"}
    # L1 ABSOLUTION (incl. paraphrase)
    if _match(ABSOLUTION_3, candidate_output):
        return {"verdict": "REFUSED", "output": "이 매개는 죄를 사할 수 없습니다. 말씀 앞에 함께 머물 뿐입니다.",
                "note": "absolution (incl. paraphrase)"}
    # L1 SCOPE
    if _match(OUT_OF_SCOPE, candidate_output):
        return {"verdict": "REDIRECTED", "output": "법률·의료·재무는 제 영역이 아닙니다. 전문가에게.",
                "note": "out-of-scope"}
    # L1 NO-ADJUDICATION
    if _match(ADJUDICATION, candidate_output):
        return {"verdict": "REDIRECTED", "output": "교파 우열을 판정하지 않습니다.", "note": "doctrinal adjudication"}
    # L1 APPLICATION-HARM heuristic -> FLAG + L3 audit (PARTIAL — not a solve)
    if _match(RISKY_ACTION_3, candidate_output):
        _audit("application-harm", user_input, candidate_output)
        return {"verdict": "FLAGGED", "output": "성구를 위험한 행동의 정당화로 적용할 수 없습니다. (인간 감사 회부)",
                "note": "application-harm — PARTIAL, routed to L3 human audit"}
    # L2 SEMANTIC HOOK (LLM-Guardian) — stub; in deployment catches paraphrase/intent + routes to L3
    sem = semantic_intent_check(user_input, candidate_output)
    if sem:
        _audit("semantic-intent", user_input, candidate_output)
        return {"verdict": "FLAGGED", "output": sem.get("msg", "의도 검토 필요 (인간 감사)"), "note": "semantic L2"}
    # L1 GROUNDING fail-closed
    ungrounded = [ref for (q, ref) in citations if not scripture_grounded(q, ref)]
    if ungrounded:
        return {"verdict": "FAIL_CLOSED", "output": "(검증 성구 없음 — 인용 중단, 임의생성 안 함)",
                "ungrounded": ungrounded, "note": "no fabrication"}
    return {"verdict": "PASS", "output": candidate_output}
