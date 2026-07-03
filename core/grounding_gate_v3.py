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
from grounding_gate import (  # noqa: E402
    scripture_grounded, CRISIS_RESPONSE, crisis_response, crisis_checkin,
    CRISIS_CHECKIN_PATTERNS, CRISIS_IDEATION, semantic_distress_check, _has_korean,
    end_wish_is_crisis, SCRIPTURE,
)
import normalization as _norm  # noqa: E402  — stdlib R8 view generator (NFKC/skeleton/decoded blobs)
from grounding_gate_v2 import (  # noqa: E402
    SELF_HARM, HARM_OTHERS, CONFIDENTIAL_REQ, CONFIDENTIAL_LEAK,
    ABSOLUTION, OUT_OF_SCOPE, ADJUDICATION, RISKY_ACTION,
)

# --- L1 patched pattern sets (brittle floor — explicitly whack-a-mole over Round-2 finds) ---
# TIER 1 (high-confidence self-harm): existing finds + oblique finality / "affairs in order".
SELF_HARM_3 = SELF_HARM + [
    r"disappear\s*forever", r"nothing\s*matters", r"사라져\s*버리",
    # finality / putting-affairs-in-order — oblique but high-signal (mirrors grounding_gate Tier 1)
    r"다\s*정리하?(고|는|려)", r"마지막\s*인사", r"유서", r"편해지고\s*싶",
    r"putting\s*(my\s*)?affairs\s*in\s*order", r"final\s*goodbye", r"won'?t\s*be\s*(here|around)",
] + CRISIS_IDEATION  # suicidal ideation promoted to Tier-1 OVERRIDE (single-sourced)
# TIER 2 (low-threshold oblique distress): imported from grounding_gate so both gates share one
# source of truth. Routes to a GENTLE check-in, not a hard escalation. Over-triggers on purpose.
CHECKIN_3 = CRISIS_CHECKIN_PATTERNS
ABSOLUTION_3 = ABSOLUTION + [r"깨끗합니다", r"씻겼", r"잘못\s*없", r"자유롭", r"clean\s*now", r"무죄"]
CONFIDENTIAL_REQ_3 = CONFIDENTIAL_REQ + [r"사람들이.*고백", r"주로.*고백", r"이번\s*주.*고백", r"다들.*고백"]
RISKY_ACTION_3 = RISKY_ACTION + [r"다\s*걸고", r"베팅", r"올인", r"한\s*번에.*걸", r"전\s*재산.*걸"]
# over-trigger fix: 복수 (revenge) but NOT 복수초(flower)/복수형(plural)/복수판/복수절
HARM_OTHERS_3 = [p for p in HARM_OTHERS if p != r"복수"] + [r"복수(?!초|형|판|절)"]


def _strip(t: str) -> str:
    return re.sub(r"\s+", "", t or "")


def _match(patterns, text: str) -> bool:
    """Match patterns over R8 NORMALIZED VIEWS (union), each also whitespace-stripped.

    Views = original + NFKC + UTS#39 skeleton + combining-stripped + decoded base64/hex blobs
    (from normalization.normalized_views). Previously v3 only whitespace-stripped, so a crisis
    intent written in homoglyphs / fullwidth / zero-width / base64 reached PASS on the SHIPPED
    run_turn('auto')=v3 path while the R8 pre-pass sat unreachable in v4/v5 (Codex 2026-07-03).
    Wiring it here closes the obfuscation gap for the shipped floor while staying stdlib-only
    (normalization is stdlib; v4's subprocess Guardian is NOT pulled in). Union = fail-closed
    direction: a false-positive on a decoded blob is a cautious block, a miss is the worst case."""
    try:
        views, _flags = _norm.normalized_views(text)
    except Exception:
        views = [text or ""]
    for v in views:
        vs = _strip(v)
        for p in patterns:
            if re.search(p, v, re.I) or re.search(p, vs, re.I):
                return True
    return False


# ── Output-text scripture grounding (Hole 1, Codex 2026-07-03) ────────────────
# The citations-channel check only validated the explicitly-passed `citations` list. A fabricated
# scripture claim written directly in candidate_output — e.g. "…God helps those who help themselves.
# (Proverbs 14:23)" — with citations=[] PASSed, because the ungrounded loop was empty. Contract is
# "nothing fabricated", so an inline scripture-shaped reference must be backed by a GROUNDED citation.
# Low-FP: only book names that actually exist in the scripture DB are treated as references (so
# "Meeting 2:30" or "see you at 3:30" are not flagged).
_KNOWN_BOOKS = sorted({ref.rsplit(" ", 1)[0] for ref in SCRIPTURE if ":" in ref.rsplit(" ", 1)[-1]},
                      key=len, reverse=True)
# re.I: a lowercase real-book ref ("proverbs 14:23") was invisible and PASSed (Codex 2026-07-03).
# Err-safe tradeoff: a benign common-word collision ("job 3:1 ratio") over-blocks to FAIL_CLOSED,
# the safe direction for a "nothing fabricated" grounding floor.
_REF_RES = [(b, re.compile(re.escape(b) + r"\s+(\d+:\d+)", re.I)) for b in _KNOWN_BOOKS]


def _output_scripture_refs(text: str):
    """Return the set of 'Book Ch:Vs' references that appear in the output AND name a real DB book."""
    t = text or ""
    refs = set()
    for book, rx in _REF_RES:
        for m in rx.finditer(t):
            refs.add("%s %s" % (book, m.group(1)))
    return refs


def _norm_txt(s: str) -> str:
    """Lenient presence view: lowercase, drop all non-alphanumeric (incl. Korean) for substring test."""
    return re.sub(r"[^0-9a-z가-힣]+", "", (s or "").lower())


def _clean_citations(citations):
    """Coerce caller citations to well-formed (quote:str, ref:str) pairs. Malformed entries
    (None / non-str / wrong arity / non-indexable) become an unmatchable pair → ungrounded →
    FAIL_CLOSED, never a crash or a PASS (Codex round-2 2026-07-03: malformed metadata must safe-fail)."""
    if not isinstance(citations, (list, tuple)):
        return []  # top-level non-list (e.g. citations=5) → no citations, never a crash (Codex round-3)
    out = []
    for c in citations:
        # exact 2-arity list/tuple only; a str / int / dict / wrong-arity entry is malformed → safe-fail
        if not isinstance(c, (list, tuple)) or len(c) != 2:
            out.append(("", "__malformed__"))
            continue
        q, ref = c[0], c[1]
        q = q if isinstance(q, str) else ("" if q is None else str(q))
        ref = ref if isinstance(ref, str) else ("__malformed__" if ref is None else str(ref))
        out.append((q, ref))
    return out


def semantic_intent_check(user_input: str, output: str):
    """L2 HOOK — LLM-Guardian semantic classifier plugs in here for paraphrase/intent the
    regex floor cannot catch (the unbounded class). STUB (no model call). Returns a risk dict or None.
    In deployment: the Guardian agent; its verdict is JUDGED -> must be anchored by L3 human audit
    (an LLM judging an LLM is self-referential)."""
    return None


AUDIT_QUEUE = []  # L3 — FLAGGED/borderline -> privacy-safe human review (the non-self anchor / ceiling)


def _audit(reason, user_input, output):
    AUDIT_QUEUE.append({"reason": reason, "input": user_input[:60], "output": output[:60]})


def gate(user_input: str, candidate_output: str, citations: list, locale=None) -> dict:
    # Defensive: coerce non-string inputs so a bad contract safe-fails instead of crashing (Codex r8).
    if not isinstance(user_input, str):
        user_input = "" if user_input is None else str(user_input)
    if not isinstance(candidate_output, str):
        candidate_output = "" if candidate_output is None else str(candidate_output)
    # Answer in the language of the person (English base, Korean compatible). locale wins when given.
    ko = (locale or "").strip().lower() == "kr" or (not locale and _has_korean(user_input))
    # L1 SAFETY (normalized, obfuscation-resistant)
    # Tier 1 — HIGH-CONFIDENCE self-harm (also fires if a wired semantic INPUT hook returns True).
    sem_in = semantic_distress_check(user_input)
    if _match(SELF_HARM_3, user_input) or end_wish_is_crisis(user_input) or sem_in is True:
        return {"verdict": "CRISIS_OVERRIDE", "output": crisis_response(locale, user_input=user_input),
                "actions": ["escalate_to_human", "preserve_record"],
                "note": "self-harm (normalized)" + ("; semantic-input-hook" if sem_in is True and not _match(SELF_HARM_3, user_input) else "")}
    # Tier 2 — LOW-THRESHOLD oblique distress -> GENTLE check-in (not blank comfort). Over-triggers.
    if _match(CHECKIN_3, user_input):
        return {"verdict": "CRISIS_CHECKIN", "output": crisis_checkin(locale, user_input=user_input),
                "actions": ["gentle_checkin", "offer_resource"],
                "note": "oblique distress (hopelessness/anhedonia/worthlessness/burden) — softer than Tier-1"}
    if _match(HARM_OTHERS_3, user_input):
        return {"verdict": "CRISIS_OVERRIDE",
                "output": "누군가를 해하려는 길로는 함께 갈 수 없습니다. 안전을 먼저 살피세요." if ko
                          else "I cannot walk a path that sets out to harm someone. Tend to safety first.",
                "actions": ["de-escalate", "no_endorsement"], "note": "harm-to-others"}
    # L1 CONFIDENTIALITY
    if _match(CONFIDENTIAL_REQ_3, user_input) or _match(CONFIDENTIAL_LEAK, candidate_output):
        return {"verdict": "REFUSED",
                "output": "다른 분이 나눈 내용은 전하지 않습니다. (격리·비공유)" if ko
                          else "I do not pass on what another person shared. (isolated · not shared)",
                "note": "confidentiality (incl. aggregation)"}
    # L1 ABSOLUTION (incl. paraphrase)
    if _match(ABSOLUTION_3, candidate_output):
        return {"verdict": "REFUSED",
                "output": "이 매개는 죄를 사할 수 없습니다. 말씀 앞에 함께 머물 뿐입니다." if ko
                          else "This medium cannot absolve sin. It only abides with you before the word.",
                "note": "absolution (incl. paraphrase)"}
    # L1 SCOPE
    if _match(OUT_OF_SCOPE, candidate_output):
        return {"verdict": "REDIRECTED",
                "output": "법률·의료·재무는 제 영역이 아닙니다. 전문가에게." if ko
                          else "Legal, medical, and financial matters are not my domain. Please see a professional.",
                "note": "out-of-scope"}
    # L1 NO-ADJUDICATION
    if _match(ADJUDICATION, candidate_output):
        return {"verdict": "REDIRECTED",
                "output": "교파 우열을 판정하지 않습니다." if ko
                          else "I do not adjudicate which tradition is superior.",
                "note": "doctrinal adjudication"}
    # L1 APPLICATION-HARM heuristic -> FLAG + L3 audit (PARTIAL — not a solve)
    if _match(RISKY_ACTION_3, candidate_output):
        _audit("application-harm", user_input, candidate_output)
        return {"verdict": "FLAGGED",
                "output": "성구를 위험한 행동의 정당화로 적용할 수 없습니다. (인간 감사 회부)" if ko
                          else "Scripture cannot be applied to justify a dangerous action. (referred to human audit)",
                "note": "application-harm — PARTIAL, routed to L3 human audit"}
    # L2 SEMANTIC HOOK (LLM-Guardian) — stub; in deployment catches paraphrase/intent + routes to L3
    sem = semantic_intent_check(user_input, candidate_output)
    if sem:
        _audit("semantic-intent", user_input, candidate_output)
        return {"verdict": "FLAGGED",
                "output": sem.get("msg", "의도 검토 필요 (인간 감사)" if ko else "intent needs review (human audit)"),
                "note": "semantic L2"}
    # L1 GROUNDING fail-closed — (a) explicitly-passed citations (sanitized: malformed → safe-fail)
    citations = _clean_citations(citations)
    ungrounded = [ref for (q, ref) in citations if not scripture_grounded(q, ref)]
    if ungrounded:
        return {"verdict": "FAIL_CLOSED",
                "output": "(검증 성구 없음 — 인용 중단, 임의생성 안 함)" if ko
                          else "(No verified scripture — quotation halted, nothing fabricated.)",
                "ungrounded": ungrounded, "note": "no fabrication"}
    # (b) scripture-shaped references in the OUTPUT TEXT (Hole 1 + residual-3, Codex 2026-07-03).
    grounded_pairs = [(q, ref) for (q, ref) in citations if scripture_grounded(q, ref)]
    grounded_refs = {ref for (q, ref) in grounded_pairs}
    # scan the OUTPUT over normalized views too, else an obfuscated book name (Cyrillic 'Prоverbs',
    # fullwidth, zero-width) evades the raw-text ref scan and fabricates a citation (Codex round-7).
    try:
        _out_views, _ = _norm.normalized_views(candidate_output)
    except Exception:
        _out_views = [candidate_output or ""]
    out_refs = set()
    for _ov in _out_views:
        out_refs |= _output_scripture_refs(_ov)
    # (b1) an output ref with NO grounded citation → fabricated inline quote (e.g. "…(Proverbs 14:23)").
    stray = set(out_refs - grounded_refs)
    # (b2) a ref that IS grounded-cited but whose grounded quote text is ABSENT from the output → the
    #      output attributes a DIFFERENT/false quote to a real ref. Only applied when the output
    #      explicitly cites that ref (on-contract: if you cite Ch:Vs, the verified verse text must be
    #      what you present). Named residual: legitimate PARAPHRASE-with-citation over-blocks here — the
    #      err-safe direction for a "nothing fabricated" relay; verbatim-quote framing is L2/L3's domain.
    nout = _norm_txt(candidate_output)
    for (q, ref) in grounded_pairs:
        if ref in out_refs and _norm_txt(q) and _norm_txt(q) not in nout:
            stray.add(ref)
    if stray:
        return {"verdict": "FAIL_CLOSED",
                "output": "(검증 성구 없음 — 인용 중단, 임의생성 안 함)" if ko
                          else "(No verified scripture — quotation halted, nothing fabricated.)",
                "ungrounded": sorted(stray), "note": "output scripture-ref not grounded (no fabrication)"}
    return {"verdict": "PASS", "output": candidate_output}
