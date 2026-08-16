#!/usr/bin/env python3
"""
The Bible — dialogue-mode grounding extra check.

ⓐ invariant-preserving: this file does NOT modify grounding_gate.py/v2/v3/v4/v5. It is a NEW,
ADDITIVE check scoped to the character-dialogue/cathedral mode's own new risk surface, composed
with the unchanged gate via dialogue_gate.py (Unsafe-Dominant Merge, DESIGN.md §4 — the
most-unsafe verdict wins).

WHY THIS EXISTS (source-verified 2026-08-16, cross-family adversarial review + repro, not asserted)
-----------------------------------------------------------------------------------------------
grounding_gate_v3.gate()'s citation-grounding path only inspects (a) the explicitly-passed
`citations` list and (b) output substrings shaped `<KnownEnglishBook> Ch:Vs` (v3.py's _KNOWN_BOOKS
is derived from the English-only scripture DB keys). Two consequences, both reproduced directly
against grounding_gate_v3.gate:

  1. A first-person "authority formula" saying with NO citation and NO ref at all —
     e.g. "내가 진실로 진실로 너희에게 이르노니, 너의 짐은 이미 내려놓아졌다." — is invisible to
     EVERY grounding check (there is nothing to scan) and returns PASS. This is a NEW attack
     surface the old quote-only design never had (a quote always carried a ref); the dialogue
     mode's persona voice_notes actively describe using this exact formula
     (personas_dialogue.json: Jesus's "내가 진실로 진실로 너희에게 이르노니").
  2. A Korean-language book reference — e.g. "(마태복음 11:28)" — is invisible to the English-only
     `_KNOWN_BOOKS` ref scanner, so a fabricated quote paired with a Korean ref PASSes even though
     the identical case with the ref passed through `citations` correctly FAIL_CLOSEDs (the
     citations-path DOES check ref-format-agnostically via scripture_grounded; it is only the
     OUTPUT-TEXT scanner that is English-only). The entire dialogue/cathedral surface is
     Korean-facing by design (every framing_disclaimer, both cathedral.md rooms).

Both collapse to one root cause: content shaped like an authoritative/scriptural claim that is
NOT explicitly passed through `citations` is invisible to the existing grounding path, in ANY
language. This module closes that specific gap for the dialogue/cathedral mode WITHOUT touching
the shared gate other repo surfaces (the lens lookup and the plain relay mode) still rely on
unchanged.
"""
import re

# Authority-formula red flags — a first-person attribution claiming to speak AS the recorded
# figure, not a stylistic tone marker. Bilingual, mirrors the gate's own pattern-list convention.
# R10 (2026-08-16, cross-family adversarial pass #2): added "성경에 기록되었으되" (Paul's own
# attested "as it is written" idiom — an evasion this list's own author missed), single "진실로
# 이르노니" (without the doubled "진실로 진실로"), and the alternate-translation forms of the same
# formula ("assuredly, I say to you" / "I tell you the truth", both common English-Bible renderings
# the original 3-pattern English set did not cover). This list remains a CURATED, non-exhaustive
# set — same ceiling as every other regex-floor pattern list in this repo (DESIGN.md §4 R2's
# "a new paraphrase evades again"), named honestly rather than claimed complete.
AUTHORITY_FORMULA = [
    r"내가\s*진실로\s*진실로", r"진실로\s*이르노니", r"내가\s*너희에게\s*이르노니", r"주께서\s*이르시되",
    r"말씀하시기를", r"성령께서\s*이르시되", r"성경에\s*기록되었으되", r"기록된\s*바",
    r"verily\s*,?\s*i\s*say\s*unto\s*(you|thee)", r"thus\s*saith\s*the\s*lord",
    r"i\s*say\s*unto\s*(you|thee)", r"assuredly\s*,?\s*i\s*say\s*(to|unto)\s*you",
    r"i\s*tell\s*you\s*the\s*truth", r"as\s*it\s*is\s*written",
]

# Language-agnostic "(<name> <digit>+:<digit>+)" shape — catches a book-name+verse reference in
# ANY script (Korean book names included), not just the gate's English-only _KNOWN_BOOKS list.
# Deliberately loose (recall over precision, matching this repo's fail-closed direction elsewhere):
# a benign parenthetical happens to look like this only rarely, and the cost of a false positive
# here is "cite it properly", not a block on an innocent conversation.
_REF_SHAPE = re.compile(r"[(（]\s*([\w가-힣]{2,20})\s+(\d{1,3}):(\d{1,3})\s*[)）]")


# Proximity GAP (chars) allowed between a claim-shaped match and the nearest edge of a grounded
# citation's OWN occurrence in the text, before treating the match as "backed". This is a GAP
# threshold between two spans, not a window the whole quote must be squeezed inside — a verse can
# be arbitrarily long (Psalm 51:1 alone is ~140 chars) and still correctly "cover" a formula that
# immediately introduces it, as long as the two spans are adjacent. Tight enough that two
# genuinely UNRELATED sentences elsewhere in the output don't accidentally cover each other.
_PROXIMITY_GAP = 60


def find_uncited_claims(candidate_output: str, citations):
    """Return a list of reasons this output makes an authority/scripture-shaped claim that is
    NOT backed by a NEARBY grounded citation. Empty list = nothing flagged (caller still runs the
    normal gate; this function only adds coverage, it never replaces the existing checks).

    citations: the same [(quote, ref), ...] list passed to gate(). A claim-shaped match is
    "backed" only if at least one citation's quote text occurs (verbatim, case-insensitive) within
    _PROXIMITY_GAP characters of the match — this module does not verify the citation is itself
    grounded (that is the existing gate's job via scripture_grounded); it verifies that something
    RELEVANT was submitted near THIS specific claim.

    R10 FIX HISTORY (2026-08-16, cross-family adversarial pass #2, 🟥 finding #1):
    Attempt 1 used ONE global `has_citations = bool(citations)` boolean for the whole output, so
    ANY citation anywhere made every claim "backed" — pairing one legitimate grounded quote with
    an unrelated fabricated authority-formula sentence bypassed the check entirely.
    Attempt 2 switched to cardinality (N claims need N citations) — closes the count mismatch but
    NOT the exact demonstrated case, which was 1 claim + 1 (irrelevant) citation: 1 is not > 1, so
    it still passed. Verified failing before this fix, not assumed.
    This version (proximity): a claim is backed only if a grounded quote's TEXT is near it, not
    merely present somewhere in the output. Verified closing the exact demonstrated case AND still
    passing the legitimate case (formula immediately introducing its own grounded quote) — see
    core/simulate_dialogue.py cases ⑨-⑩.
    Residual, still real and named: this is textual proximity, not semantic relevance — a citation
    padded immediately adjacent to an unrelated fabricated claim (rather than genuinely far away)
    would still incorrectly read as "backed". Closing that needs span-level claim/quote
    correlation this module does not attempt; DESIGN.md §4 R2's "a regex floor is infinitely
    evadable" ceiling applies here too, named rather than claimed closed.
    """
    text = candidate_output or ""
    reasons = []
    citations = citations or []
    text_lower = text.lower()

    # Each citation quote's OWN occurrence span(s) in the raw text (case-insensitive, NOT
    # whitespace-normalized — a verse is quoted verbatim by design, so exact substring search finds
    # it directly; this also keeps character positions aligned with the claim-match positions,
    # which normalizing away whitespace would break for a long verse).
    quote_spans = []
    for (q, _ref) in citations:
        if not q:
            continue
        ql = q.lower()
        start = 0
        while True:
            idx = text_lower.find(ql, start)
            if idx < 0:
                break
            quote_spans.append((idx, idx + len(ql)))
            start = idx + 1

    def _covered(start, end):
        if not quote_spans:
            return False
        return any(
            max(start, qs) - min(end, qe) <= _PROXIMITY_GAP  # spans overlap or are within GAP chars
            for (qs, qe) in quote_spans
        )

    uncited_formula = any(
        not _covered(m.start(), m.end())
        for p in AUTHORITY_FORMULA
        for m in re.finditer(p, text, re.I)
    )
    if uncited_formula:
        reasons.append(
            "an authority-formula phrase is present with no grounded citation nearby — an uncited "
            "first-person saying attributed to the persona"
        )

    uncited_ref = any(not _covered(m.start(), m.end()) for m in _REF_SHAPE.finditer(text))
    if uncited_ref:
        reasons.append(
            "a reference-shaped span is present with no grounded citation nearby — cannot be "
            "grounding-checked in any language, English-only ref scanner cannot see a non-English one"
        )

    return reasons


def extra_check(user_input: str, candidate_output: str, citations, locale=None):
    """Returns a gate()-shaped verdict dict when this module's check fires, else None (meaning:
    defer entirely to the base gate — this module never overrides a PASS with its own PASS, it
    only ever adds a block). Compose via dialogue_gate.py, never call standalone as a substitute
    for gate()."""
    reasons = find_uncited_claims(candidate_output, citations)
    if not reasons:
        return None
    ko = bool(re.search(r"[가-힣]", user_input or ""))
    return {
        "verdict": "UNGROUNDED_ATTRIBUTION",
        "output": ("(인용 없는 발화 — 이 표현은 인용된 성구로 뒷받침되지 않습니다. 근거 없이 "
                    "전달할 수 없습니다.)" if ko else
                    "(Uncited claim — this line is not backed by a cited verse. It cannot be "
                    "surfaced without grounding.)"),
        "note": "dialogue_grounding_extra — " + "; ".join(reasons),
    }
