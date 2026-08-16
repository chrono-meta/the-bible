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
AUTHORITY_FORMULA = [
    r"내가\s*진실로\s*진실로", r"내가\s*너희에게\s*이르노니", r"주께서\s*이르시되",
    r"말씀하시기를", r"성령께서\s*이르시되",
    r"verily\s*,?\s*i\s*say\s*unto\s*(you|thee)", r"thus\s*saith\s*the\s*lord",
    r"i\s*say\s*unto\s*(you|thee)",
]

# Language-agnostic "(<name> <digit>+:<digit>+)" shape — catches a book-name+verse reference in
# ANY script (Korean book names included), not just the gate's English-only _KNOWN_BOOKS list.
# Deliberately loose (recall over precision, matching this repo's fail-closed direction elsewhere):
# a benign parenthetical happens to look like this only rarely, and the cost of a false positive
# here is "cite it properly", not a block on an innocent conversation.
_REF_SHAPE = re.compile(r"[(（]\s*([\w가-힣]{2,20})\s+(\d{1,3}):(\d{1,3})\s*[)）]")


def find_uncited_claims(candidate_output: str, citations):
    """Return a list of reasons this output makes an authority/scripture-shaped claim that is
    NOT backed by an explicit citations entry. Empty list = nothing flagged (caller still runs
    the normal gate; this function only adds coverage, it never replaces the existing checks).

    citations: the same [(quote, ref), ...] list passed to gate(). A claim is considered "backed"
    only if citations is non-empty — this module does not itself verify grounding (that is the
    existing gate's job via scripture_grounded); it only verifies that SOMETHING was submitted
    for checking, closing the "nothing was passed so nothing was checked" gap.
    """
    text = candidate_output or ""
    reasons = []
    has_citations = bool(citations)

    for p in AUTHORITY_FORMULA:
        if re.search(p, text, re.I):
            if not has_citations:
                reasons.append(
                    "authority-formula phrase present with no citations passed — an uncited "
                    "first-person saying attributed to the persona"
                )
            break  # one instance is enough to explain the class; don't spam duplicates

    m = _REF_SHAPE.search(text)
    if m and not has_citations:
        reasons.append(
            f"reference-shaped text '({m.group(0)[1:-1]})' present with no citations passed — "
            "cannot be grounding-checked in any language, English-only ref scanner cannot see it"
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
