#!/usr/bin/env python3
"""
The Bible — gate v5 = v4 (L1 floor + LLM Guardian) + R8 NORMALIZATION PRE-PASS.

Round-3 strengthening run (3b). v3's L1 only stripped whitespace, so an intent written in homoglyphs
("dіe"), fullwidth ("ｄｉｅ"), zero-width splits, or a base64/hex blob slipped past every regex
unchanged. v5 inserts a normalization PRE-PASS in front of v4: it re-runs the existing L1 safety
patterns against several NORMALIZED VIEWS of the input/output (NFKC · UTS#39 skeleton · decoded
base64/hex) and blocks if ANY view trips. This is a UNION over normalized views — recall-increasing,
fail-closed in direction.

KEY INVARIANT (round-3 discovery #1): the UTS#39 skeleton is used ONLY as a detection/matching view,
NEVER as the canonical text handed downstream. The pre-pass blocks on a normalized-view hit, otherwise
it falls through to v4 with the ORIGINAL text — so no downstream layer (Guardian, grounding) ever sees
the over-inclusive skeleton form. Skeleton-as-blocklist, not skeleton-as-remap.

OBFUSCATION-ATTEMPTED HANDLING: an input that was deliberately obfuscated (homoglyph mixed-script, or a
decoded blob) but whose de-obfuscated views did NOT trip a safety pattern is not silently PASSed — it is
FLAGGED to the L3 human audit (proportionate fail-closed: the evasion attempt is itself the signal). A
benign multilingual sentence (scripts in separate words, e.g. KR+EN) is NOT flagged (see
normalization.is_mixed_script_confusable).

CPT (round-3 discovery #2): the cited ~99.7% obfuscation detector needs a BPE tokenizer; L1 stays
stdlib-clean, so the cited-accuracy path is the optional `normalization.cpt_obfuscation_check` hook
(default None). v5 ships the stdlib floor (base64/hex decode-rescan) and honors the hook when wired.

LOCALE (round-3 discovery #3): handled in `grounding_gate._CRISIS_RESOURCES` — every locale now also
surfaces a maintained crisis directory (findahelpline / Befrienders / IASP) so a stale hardcoded hotline
can never be the only line. Coded-idiom / code-switched distress that carries no keyword is explicitly
assigned to L2/L3 (the pattern floor structurally cannot reach it) — named, not silently claimed closed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import grounding_gate_v4 as v4  # noqa: E402  (wires the real Guardian into v3.gate)
import grounding_gate_v3 as v3  # noqa: E402
import normalization as norm  # noqa: E402
from grounding_gate import scripture_grounded, crisis_response, crisis_checkin, _has_korean  # noqa: E402

# Pattern sets re-used from v3 (single source of truth — v5 adds no new patterns, only new VIEWS).
from grounding_gate_v3 import (  # noqa: E402
    SELF_HARM_3, CHECKIN_3, HARM_OTHERS_3, CONFIDENTIAL_REQ_3, ABSOLUTION_3, RISKY_ACTION_3, _match,
)
from grounding_gate_v2 import CONFIDENTIAL_LEAK, OUT_OF_SCOPE, ADJUDICATION  # noqa: E402


def _match_any_view(patterns, views) -> bool:
    """True if any normalized view of the text trips any pattern (union over views)."""
    return any(_match(patterns, v) for v in views)


def gate(user_input: str, candidate_output: str, citations: list, locale=None) -> dict:
    ko = (locale or "").strip().lower() == "kr" or (not locale and _has_korean(user_input))
    in_views, in_flags = norm.normalized_views(user_input)
    out_views, _ = norm.normalized_views(candidate_output)

    # --- R8 NORMALIZATION PRE-PASS: re-run the L1 floor over normalized views (skeleton = detect-only) ---
    # Tier 1 — high-confidence self-harm, now across homoglyph/fullwidth/zero-width/encoded views.
    if _match_any_view(SELF_HARM_3, in_views):
        return {"verdict": "CRISIS_OVERRIDE",
                "output": crisis_response(locale, user_input=user_input),
                "actions": ["escalate_to_human", "preserve_record"],
                "note": "self-harm (normalized-view: homoglyph/fullwidth/zero-width/encoded)"}
    # Tier 2 — oblique distress over views (gentle check-in).
    if _match_any_view(CHECKIN_3, in_views):
        return {"verdict": "CRISIS_CHECKIN", "output": crisis_checkin(locale, user_input=user_input),
                "actions": ["gentle_checkin", "offer_resource"],
                "note": "oblique distress (normalized-view)"}
    if _match_any_view(HARM_OTHERS_3, in_views):
        return {"verdict": "CRISIS_OVERRIDE",
                "output": "누군가를 해하려는 길로는 함께 갈 수 없습니다. 안전을 먼저 살피세요." if ko
                          else "I cannot walk a path that sets out to harm someone. Tend to safety first.",
                "actions": ["de-escalate", "no_endorsement"], "note": "harm-to-others (normalized-view)"}
    # Confidentiality / absolution / scope / adjudication / application-harm over OUTPUT views.
    if _match_any_view(CONFIDENTIAL_REQ_3, in_views) or _match_any_view(CONFIDENTIAL_LEAK, out_views):
        return {"verdict": "REFUSED",
                "output": "다른 분이 나눈 내용은 전하지 않습니다. (격리·비공유)" if ko
                          else "I do not pass on what another person shared. (isolated · not shared)",
                "note": "confidentiality (normalized-view)"}
    if _match_any_view(ABSOLUTION_3, out_views):
        return {"verdict": "REFUSED",
                "output": "이 매개는 죄를 사할 수 없습니다. 말씀 앞에 함께 머물 뿐입니다." if ko
                          else "This medium cannot absolve sin. It only abides with you before the word.",
                "note": "absolution (normalized-view)"}
    if _match_any_view(OUT_OF_SCOPE, out_views):
        return {"verdict": "REDIRECTED",
                "output": "법률·의료·재무는 제 영역이 아닙니다. 전문가에게." if ko
                          else "Legal, medical, and financial matters are not my domain. Please see a professional.",
                "note": "out-of-scope (normalized-view)"}
    if _match_any_view(ADJUDICATION, out_views):
        return {"verdict": "REDIRECTED",
                "output": "교파 우열을 판정하지 않습니다." if ko
                          else "I do not adjudicate which tradition is superior.",
                "note": "doctrinal adjudication (normalized-view)"}
    if _match_any_view(RISKY_ACTION_3, out_views):
        v3._audit("application-harm (normalized-view)", user_input, candidate_output)
        return {"verdict": "FLAGGED",
                "output": "성구를 위험한 행동의 정당화로 적용할 수 없습니다. (인간 감사 회부)" if ko
                          else "Scripture cannot be applied to justify a dangerous action. (referred to human audit)",
                "note": "application-harm (normalized-view) — PARTIAL, routed to L3"}

    # --- Obfuscation attempted but de-obfuscated views were clean -> FLAG to L3 (don't silently PASS) ---
    # The evasion attempt is itself the signal. Proportionate: a human-audit FLAG, not a hard refuse.
    if in_flags["obfuscation_attempted"]:
        sig = []
        if in_flags["homoglyph"]:
            sig.append("homoglyph")
        if in_flags["suspicious_format"]:
            sig.append("zero-width/bidi")
        if in_flags["cpt"] is True:
            sig.append("low-CPT")
        v3._audit("obfuscation-attempt", user_input, candidate_output)
        return {"verdict": "FLAGGED",
                "output": ("입력에 난독화 시도가 감지되어 사람 감사로 회부합니다." if ko
                           else "Obfuscation was detected in the input; referring to human audit."),
                "note": "obfuscation-attempt (" + ", ".join(sig) + ") — clean after de-obfuscation, L3 review"}

    # --- Clean of normalized-view hits: delegate to v4 (L2 Guardian + grounding) on the ORIGINAL text ---
    # Downstream never sees the skeleton/normalized form — only the user's actual text.
    return v4.gate(user_input, candidate_output, citations, locale)


semantic_intent_check = v4.semantic_intent_check
