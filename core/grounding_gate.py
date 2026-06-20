#!/usr/bin/env python3
"""
The Bible — core grounding gate (proof-of-keystone for the HARDENED design).

Mechanizes the safety fixes this design requires.
Scripture itself is the ABSOLUTE axiom: this system does NOT verify scripture — it only
constrains the AI's OUTPUT to stay grounded in the verified DB, and forces safety to win.

Three keystones, in precedence order:
  (2) CRISIS-OVERRIDE   — self-harm / harm signals override EVERYTHING (comfort architecture
                          AND the no-trace destruction): escalate to a human/crisis resource,
                          preserve the record for duty-of-care. (safety > comfort.)
  (1) SCRIPTURE-GROUNDING, FAIL-CLOSED — the AI may emit a verse ONLY if it matches the verified
                          DB exactly. Fabricated/misquoted scripture -> no doctrinal output.
                          (mechanical source-grounding: constrains the OUTPUT to the verified source, not scripture itself.)
  (-) HONEST FRAMING    — scripture-mediation reflection, NOT sacramental confession; confers no
                          absolution. (residual named, not hidden — see DESIGN.md.)

Gates (not a full system). Scripture = a real multi-version public-domain corpus
(core/scripture/*.json — KJV·WEB·ASV·YLT Protestant + Douay-Rheims Catholic + KJVA Apocrypha),
with core/scripture_db.json as a mock fallback if the corpus is absent.
"""
import json
import os
import re

DB_DIR = os.path.join(os.path.dirname(__file__), "scripture")
DB_MOCK = os.path.join(os.path.dirname(__file__), "scripture_db.json")


def _load_corpus():
    """Full multi-version corpus (core/scripture/*.json). Each version is the ABSOLUTE
    axiom in its tradition; grounding accepts a quote verified in ANY version — non-biased
    by construction (KJV·WEB·ASV·YLT Protestant + Douay-Rheims Catholic + KJVA Apocrypha).
    Falls back to the mock DB if the corpus is absent (gate stays runnable standalone)."""
    versions = {}
    if os.path.isdir(DB_DIR):
        for fn in sorted(os.listdir(DB_DIR)):
            if fn.endswith(".json") and not fn.startswith("_"):
                data = json.load(open(os.path.join(DB_DIR, fn), encoding="utf-8"))
                versions[fn[:-5]] = {k: v for k, v in data.items() if not k.startswith("_")}
    if not versions:  # fallback: mock single-version DB
        data = json.load(open(DB_MOCK, encoding="utf-8"))
        versions["mock"] = {k: v for k, v in data.items() if not k.startswith("_")}
    return versions


SCRIPTURE_VERSIONS = _load_corpus()
# flattened union view (any-version) for callers expecting a single {ref: text}
SCRIPTURE = {ref: text for ver in SCRIPTURE_VERSIONS.values() for ref, text in ver.items()}

# Illustrative crisis signals. Real deployment needs a vetted classifier + locale-correct resources.
CRISIS_PATTERNS = [
    r"죽고\s*싶", r"사라지고\s*싶", r"자해", r"끝내\s*버리", r"살\s*이유.*없",
    r"kill\s*myself", r"suicid", r"end\s*it\s*all", r"self[\s-]*harm", r"don'?t\s*want\s*to\s*live",
]
CRISIS_RESPONSE = (
    "지금 많이 힘드신 것 같습니다. 이건 혼자 감당할 일이 아니고, 지금 바로 사람에게 닿아야 합니다.\n"
    "  · 자살예방상담 109 (24시간)   · 정신건강위기상담 1577-0199\n"
    "(이 매개는 위기를 대신 감당할 수 없습니다 — 사람에게 연결하는 것이 먼저입니다.)"
)


def detect_crisis(user_input: str) -> bool:
    return any(re.search(p, user_input, re.I) for p in CRISIS_PATTERNS)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


# Governing tokens whose omission can INVERT a quote's meaning (negation / attribution).
# A sub-span quote that drops a preceding governing clause is suspicious truncation.
_GOVERNING_PREFIX = re.compile(
    r"\b(no|not|never|nor|none|cannot|without|said|saith|says|say)\b|없|아니|말라|못|말하|이르되|가로되",
    re.I,
)


def _truncation_inverts(prefix: str) -> bool:
    """True if the omitted LEADING text carries a negation/attribution clause that governs
    (and can invert) the quoted span — e.g. 'The fool hath said in his heart,' before
    'There is no God'. Targets polarity-inverting truncation, not benign partial quotes."""
    return bool(_GOVERNING_PREFIX.search(prefix))


def scripture_grounded(quote: str, ref: str) -> bool:
    """Grounded ONLY if SOME verified version has this ref AND its canonical passage
    (normalized) contains the quoted text AS A MEANING-PRESERVING SPAN. Multi-version union:
    a quote verified in ANY tradition (Protestant KJV/WEB/ASV/YLT · Catholic Douay-Rheims ·
    Apocrypha KJVA) counts. No verified match in any version -> not grounded -> fail-closed.

    Truncation guard (2026-06-20): substring grounding alone let a real verse be sliced
    mid-clause to invert its meaning (e.g. 'There is no God' from 'The fool hath said in his
    heart, There is no God' / Psalm 14:1). A sub-span that starts mid-verse is now rejected
    when the omitted leading text carries a governing negation/attribution clause. Whole-verse
    and boundary-aligned partial quotes still pass. Named residual: full meaning-preservation
    is undecidable; this closes the demonstrated polarity-inversion class only — the harmful-
    FRAMING class (a whole, true verse used harmfully) and trailing-clause drops remain the
    L2 (semantic Guardian) / L3 (human audit) backstop, per DESIGN §5."""
    nq = _norm(quote)
    if not nq:
        return False
    for ver in SCRIPTURE_VERSIONS.values():
        text = ver.get(ref)
        if not text:
            continue
        nt = _norm(text)
        if nq == nt:
            return True  # whole verse — always grounded
        start = nt.find(nq)
        while start != -1:
            if start == 0 or not _truncation_inverts(nt[:start]):
                return True  # verse-start or benign mid-verse partial
            start = nt.find(nq, start + 1)  # suspicious here; check any later occurrence
    return False


def gate(user_input: str, candidate_output: str, citations: list) -> dict:
    """citations: list of (quote, ref) tuples the candidate_output relies on."""
    # (2) CRISIS-OVERRIDE — highest precedence; overrides comfort + no-trace destruction.
    if detect_crisis(user_input):
        return {
            "verdict": "CRISIS_OVERRIDE",
            "output": CRISIS_RESPONSE,
            "actions": ["escalate_to_human", "preserve_record (override Vault destruction)"],
            "note": "safety > comfort; 'total acceptance' architecture suspended",
        }
    # (1) SCRIPTURE-GROUNDING, FAIL-CLOSED — every cited verse must match the verified DB.
    ungrounded = [ref for (quote, ref) in citations if not scripture_grounded(quote, ref)]
    if ungrounded:
        return {
            "verdict": "FAIL_CLOSED",
            "output": "(검증된 성구를 찾지 못해 성구 인용을 중단합니다. 임의 생성하지 않습니다.)",
            "ungrounded": ungrounded,
            "note": "AI may not emit scripture absent a verified-DB match; no fabrication",
        }
    return {"verdict": "PASS", "output": candidate_output}


if __name__ == "__main__":
    print("=== The Bible — core gate, proof of keystones ===\n")
    cases = [
        (
            "평안을 구합니다",
            'Come unto me, all ye that labour and are heavy laden, and I will give you rest. (Matthew 11:28)',
            [("Come unto me, all ye that labour and are heavy laden, and I will give you rest.", "Matthew 11:28")],
            "GROUNDED — 검증 성구 정확 인용 → PASS 기대",
        ),
        (
            "위로가 필요해요",
            'God helps those who help themselves. (Proverbs 14:23)',  # NOT in the Bible — famous misattribution
            [("God helps those who help themselves.", "Proverbs 14:23")],
            "FABRICATED — 성경에 없는 구절 → FAIL_CLOSED 기대",
        ),
        (
            "더 살 이유가 없는 것 같아요",  # crisis
            "(어떤 성구 응답이든)",
            [],
            "CRISIS — 성구보다 사람 먼저 → CRISIS_OVERRIDE 기대",
        ),
        (
            "신앙이 흔들려요",
            'Scripture says: "There is no God." (Psalms 14:1)',  # REAL verse, sliced mid-clause to invert meaning
            [("There is no God", "Psalms 14:1")],
            "TRUNCATION — 진짜 구절을 절단해 의미반전(부정절 탈락) → FAIL_CLOSED 기대 (substring-grounding 우회 차단)",
        ),
    ]
    for ui, out, cites, label in cases:
        r = gate(ui, out, cites)
        print(f"[{label}]")
        print(f"  input  : {ui}")
        print(f"  verdict: {r['verdict']}")
        print(f"  output : {r['output'].splitlines()[0]}")
        if r.get("ungrounded"):
            print(f"  ungrounded: {r['ungrounded']}")
        if r.get("actions"):
            print(f"  actions: {r['actions']}")
        print()
