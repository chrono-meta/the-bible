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

# --- Crisis signal tiers (illustrative; real deployment needs a vetted classifier) ---
# TIER 1 — HIGH-CONFIDENCE: explicit self-harm / death-wish / finality. Escalate HARD.
#   This is the existing high-confidence path. Do NOT weaken it — these MUST always escalate.
CRISIS_PATTERNS = [
    r"죽고\s*싶", r"사라지고\s*싶", r"자해", r"끝내\s*버리", r"살\s*이유.*없",
    r"kill\s*myself", r"suicid", r"end\s*it\s*all", r"self[\s-]*harm", r"don'?t\s*want\s*to\s*live",
    # finality / "putting affairs in order" — oblique but high-signal toward self-harm
    r"다\s*정리하?(고|는|려)", r"마지막\s*인사", r"유서", r"이제\s*편해지?", r"편해지고\s*싶",
    r"putting\s*(my\s*)?affairs\s*in\s*order", r"final\s*goodbye", r"won'?t\s*be\s*(here|around)",
]

# TIER 1 — SUICIDAL IDEATION (promoted from CHECKIN). "Better off without me" / self-as-relief-
#   by-disappearance, and death-wish phrasings the keyword list missed, are GENUINE crises and
#   MUST hard-escalate (OVERRIDE), not a soft check-in. False-positive here = a wrong hard
#   escalation (safe direction); false-negative = a missed crisis (worst, per design ranking).
#   Self-reference is required on the disappearance forms so benign "걱정이 사라지면" / "비가
#   없으면 다들 좋아" do NOT trigger. Single-sourced: v3's SELF_HARM_3 imports this list.
CRISIS_IDEATION = [
    r"그만\s*살", r"없어지고\s*싶", r"더는?\s*못\s*살",
    r"(이번이|이게|오늘이)\s*마지막",
    r"(내가|나|날)\s*(없어지|사라지)면", r"(내가|나)\s*없으면.*(편|좋|나아|행복)",
    r"없는\s*게\s*(낫|나아|좋)",
    r"better\s*off\s*without\s*me", r"no\s*reason\s*to\s*live",
    r"want\s*to\s*disappear", r"wish\s*i\s*(was|were)\s*(dead|gone)",
]
CRISIS_PATTERNS = CRISIS_PATTERNS + CRISIS_IDEATION

# --- Ambiguous "끝내/끝나고 싶" discriminator (round-3 3c, Case-C refinement) ---
# "(끝내|끝나)고 싶" conflates ending a LIFE (crisis) with finishing a TASK ("이 빚 문제를 끝내고
# 싶어" = resolve a debt — benign). It used to sit in CRISIS_IDEATION (Tier-1), hard-escalating every
# benign task-completion (Case C). The UNAMBIGUOUS self-harm form "끝내 버리" stays in CRISIS_PATTERNS
# (Tier-1) untouched, so demoting the ambiguous form loses no high-confidence signal.
#
# This is NOT a Tier-1->Tier-2 demotion (Tier-2 still blocks, so it would not fix the Case-C FP and
# WOULD weaken genuine-crisis response). It is a context discriminator with a FAIL-SAFE default:
# ambiguous/bare -> crisis (Tier-1, unchanged); a self/life/totality marker -> ALWAYS crisis
# (overrides any task noun); ONLY an explicit concrete task object with no self-marker is suppressed.
# Direction of error stays safe: a missed crisis is the worst outcome (design ranking), so suppression
# requires positive evidence of a benign task object, never the absence of a crisis marker.
_END_WISH = re.compile(r"(끝내|끝나)\s*고?\s*싶")
# self / life / totality — if present, ALWAYS crisis regardless of any task noun.
_END_SELF_TOTALITY = re.compile(
    r"(삶|인생|살기|사는\s*게|목숨|생(을|이|마저)|"
    r"다\s*(끝|놓|그만)|모든\s*(걸|것|게)\s*(다\s*)?끝|이제\s*그만|전부\s*다|"
    r"내\s*(자신|존재)|나\s*(자신|를))"
)
# DANGER CONTEXT — death / survival / existence / unbearable-pain markers ANYWHERE in the utterance.
# If any co-occurs with an end-wish, it is a crisis regardless of any task noun. This closes the
# cross-family-found FN class (codex gpt-5.5, round-3 3c): an abstract container noun ("이 문제/상황을
# 끝내고 싶어") was suppressing genuine crises whose death/existence context sat OUTSIDE the self regex
# ("죽을 용기도 없고…", "내 생존 문제를…", "my life 문제를…"). The end-wish gates this, so a broad
# substring match here is safe (it only fires when "끝내/끝나고 싶" is also present).
_END_DANGER_CONTEXT = re.compile(
    r"(죽|자살|목숨|생존|살아\s*있|살\s*(가치|이유|아갈|아야)|사는\s*(게|것)|숨(을|쉬|이)|"
    r"사라지|없어지|더는?\s*못\s*살|그만\s*살|고통|통증|괴로(움|워|운)|"
    r"버틸\s*수\s*없|더\s*못\s*버티|"
    r"life|alive|exist|suicid|kill\s*myself|no\s*reason\s*to\s*live)",
    re.I,
)
# concrete NON-self task objects that legitimately take "끝내고 싶" (finish/resolve), within a short
# window BEFORE the end-wish. Deliberately concrete — a vague noun must NOT suppress a crisis. The
# abstract containers 문제/상황 are intentionally EXCLUDED (too life-conflatable, cross-family FN);
# a bare "이 문제를 끝내고 싶어" with no concrete object now fails safe to crisis. Case C still
# suppresses via the concrete "빚".
_END_TASK_OBJECT = re.compile(
    r"(빚|대출|돈|일|업무|작업|숙제|과제|프로젝트|공부|시험|게임|회의|"
    r"관계|싸움|논쟁|드라마|영화|책|이\s*(것|거|걸))"
    r"\S*\s*(?:을|를|이|가|은|는|만)?\s*(?:\S+\s+){0,3}?(끝내|끝나)\s*고?\s*싶"
)


def end_wish_is_crisis(text: str) -> bool:
    """True if an ambiguous '끝내/끝나고 싶' should be treated as a Tier-1 crisis signal.
    FAIL-SAFE: returns False only when the phrase is bound to a concrete task object AND neither a
    self/life/totality marker NOR a death/existence DANGER-context marker is present anywhere.
    Bare/ambiguous -> True (crisis). Phrase absent -> False."""
    t = text or ""
    if not _END_WISH.search(t):
        return False
    if _END_SELF_TOTALITY.search(t) or _END_DANGER_CONTEXT.search(t):
        return True            # life/totality OR death/existence context -> always crisis
    if _END_TASK_OBJECT.search(t):
        return False           # concrete task object, no danger marker -> benign (finishing a task)
    return True                # bare/ambiguous -> fail-safe crisis

# TIER 2 — LOW-THRESHOLD CHECK-IN: oblique hopelessness / anhedonia / worthlessness /
#   burden-to-others. These are NOT explicit, so they route to a GENTLE check-in + resource
#   rather than straight comfort. By design this OVER-TRIGGERS: a false positive here is a
#   gentle "are you okay?" — a false NEGATIVE is a missed crisis, the worst outcome. We accept
#   the false positives on purpose.
CRISIS_CHECKIN_PATTERNS = [
    # hopelessness / meaninglessness
    r"의미\s*없", r"부질없", r"덧없", r"희망(이)?\s*없", r"소용\s*없", r"나아질\s*(것\s*)?같지\s*않",
    r"meaningless", r"no\s*point", r"point(less)?\s*(in|to)?\s*(anything|living)?", r"hopeless",
    r"nothing\s*matters", r"what'?s\s*the\s*point",
    # anhedonia / exhaustion ("just tired", "can't go on")
    r"그냥\s*(좀\s*)?지(쳤|쳐|친다)", r"지쳤", r"지친다", r"버틸\s*수\s*없", r"더\s*못\s*버티",
    r"so\s*tired", r"can'?t\s*(go\s*on|keep\s*going|do\s*this\s*anymore)", r"exhausted\s*by\s*everything",
    # worthlessness
    r"쓸모\s*없", r"가치\s*없", r"내가\s*뭐라고", r"worthless", r"no\s*good\s*to\s*anyone",
    # burden-to-others
    r"짐(이|만)?\s*(되|돼|될)", r"부담(만)?\s*(되|줘|주)", r"나\s*없으면\s*(다들|편)", r"없는\s*게\s*나",
    r"burden\s*to\s*(everyone|anyone|others|them|you)", r"better\s*off\s*without\s*me",
    # loneliness / wanting to vanish (softer than TIER-1 "사라지고 싶")
    r"혼자(인|라|예요|에요|야)?", r"외롭", r"사라지(고|면|니|는|버)", r"all\s*alone", r"(so\s*)?lonely",
]

# NAMED RESIDUAL (honest — pattern lists are infinitely evadable): these two tiers raise the
# floor but do NOT close the oblique-distress class. A paraphrase with none of these tokens
# ("the colors have gone out of things", a metaphor in any language) still slips both tiers.
# That is WHY (a) Tier 2 over-triggers on purpose — false positives are cheap, the false NEGATIVE
# (missed crisis) is the worst outcome by design ranking — AND (b) semantic_distress_check() exists
# as an INPUT-side L2 hook, AND (c) v3's L3 human-audit anchor remains the irreducible ceiling
# (a pattern list, like an LLM judge, is foolable; named, not hidden).

# Locale-keyed crisis resources. Stop hardcoding Korea-only. INTERNATIONAL is the fallback
# when locale is unknown — better a "find your local line" than a wrong/unreachable number.
# Round-3 #3: EVERY locale (not only unknown) also surfaces a maintained crisis DIRECTORY, so a stale
# hardcoded hotline can never be the only line — the local number may change, the directory is curated.
_CRISIS_DIRECTORY = (
    "  · Crisis directory (kept current): https://findahelpline.com · "
    "https://befrienders.org · https://www.iasp.info/crisis-centres-helplines/"
)
_CRISIS_RESOURCES = {
    "kr": "  · 자살예방상담 109 (24시간)   · 정신건강위기상담 1577-0199\n" + _CRISIS_DIRECTORY,
    "us": "  · 988 Suicide & Crisis Lifeline (call or text 988, 24/7)\n" + _CRISIS_DIRECTORY,
    "gb": "  · Samaritans 116 123 (free, 24/7)   · text SHOUT to 85258\n" + _CRISIS_DIRECTORY,
    "international": (
        "  · Find a local crisis line: https://findahelpline.com  (or your country's emergency number)\n"
        + _CRISIS_DIRECTORY + "\n"
        "  · If you are in immediate danger, contact local emergency services now."
    ),
}


def _has_korean(text) -> bool:
    """True if the text contains Hangul. Used to answer a crisis in the language it was spoken in —
    the tool's base is English (international), with Korean kept fully compatible."""
    return bool(re.search(r"[가-힣]", text or ""))


# Crisis response bodies, one per language. The {res} placeholder receives the locale resource line.
_CRISIS_BODY = {
    "ko": (
        "지금 많이 힘드신 것 같습니다. 이건 혼자 감당할 일이 아니고, 지금 바로 사람에게 닿아야 합니다.\n"
        "{res}\n"
        "(이 매개는 위기를 대신 감당할 수 없습니다 — 사람에게 연결하는 것이 먼저입니다.)"
    ),
    "en": (
        "It sounds like you are carrying a great deal right now. This is not something to face alone —\n"
        "please reach a person now.\n"
        "{res}\n"
        "(This medium cannot carry a crisis for you — connecting you to a person comes first.)"
    ),
}


def crisis_response(locale=None, user_input=None) -> str:
    """Locale-appropriate crisis resource, answered in the language of the person in crisis.
    English (international) is the base; Korean stays fully compatible. Precedence:
      - locale='kr'                  -> Korean body + Korean lines (109/1577-0199).
      - a KNOWN non-kr locale        -> English body + that country's line (e.g. 'us' -> 988).
      - an UNKNOWN/'international' code -> INTERNATIONAL fallback ONLY (no wrong hardcoded number).
      - no locale given              -> infer from the INPUT language: a Korean input gets the
                                         Korean body + Korean lines + international fallback;
                                         any other input gets the English body + international
                                         fallback.
    The key safety distinction: an *unknown* locale must never surface a wrong hardcoded number."""
    key = (locale or "").strip().lower()
    if key == "kr":
        return _CRISIS_BODY["ko"].format(res=_CRISIS_RESOURCES["kr"])
    if key and key in _CRISIS_RESOURCES and key != "international":
        return _CRISIS_BODY["en"].format(res=_CRISIS_RESOURCES[key])
    if key:  # a code was given but we don't have a line for it (incl. explicit 'international').
        return _CRISIS_BODY["en"].format(res=_CRISIS_RESOURCES["international"])
    # No locale: answer in the language of the input. Korean input -> Korean; otherwise English.
    if _has_korean(user_input):
        return _CRISIS_BODY["ko"].format(
            res=f"{_CRISIS_RESOURCES['kr']}\n{_CRISIS_RESOURCES['international']}"
        )
    return _CRISIS_BODY["en"].format(res=_CRISIS_RESOURCES["international"])


# Backward-compatible default response (used by v2/v3 imports). English/international base — no
# input context at module load, so it falls to the English body.
CRISIS_RESPONSE = crisis_response()

# Gentle check-in body for TIER-2 oblique distress — NOT a hard crisis escalation, but NOT
# blank comfort either: it names the feeling, asks directly, and surfaces a resource. Same
# input-language rule as crisis_response (English base, Korean compatible).
def crisis_checkin(locale=None, user_input=None) -> str:
    key = (locale or "").strip().lower()
    speak_ko = (key == "kr") or (not key and _has_korean(user_input))
    if not key:
        res = _CRISIS_RESOURCES["kr"] if speak_ko else _CRISIS_RESOURCES["international"]
    else:
        res = _CRISIS_RESOURCES.get(key, _CRISIS_RESOURCES["international"])
    if speak_ko:
        return (
            "마음이 많이 가라앉아 있는 것처럼 들립니다. 혹시 지금 안전하신가요? 괜찮지 않다면 혼자 두지 않겠습니다.\n"
            f"{res}\n"
            "(힘든 마음을 가볍게 흘려보내지 않으려 여쭙니다 — 언제든 사람에게 닿으셔도 됩니다.)"
        )
    return (
        "It sounds like your heart is weighed down right now. Are you safe at the moment? If you are\n"
        "not okay, I will not leave you alone with it.\n"
        f"{res}\n"
        "(I ask so as not to wave a heavy heart away — you may reach a person at any time.)"
    )


def detect_crisis(user_input: str) -> bool:
    """HIGH-CONFIDENCE crisis detection (Tier 1). True -> hard escalate."""
    return any(re.search(p, user_input, re.I) for p in CRISIS_PATTERNS) or end_wish_is_crisis(user_input)


def detect_checkin(user_input: str) -> bool:
    """LOW-THRESHOLD oblique-distress detection (Tier 2). True -> gentle check-in + resource.
    Deliberately over-triggers; a false positive is a kind question, a false negative is a
    missed crisis. Tier 1 takes precedence (checked first in gate())."""
    return any(re.search(p, user_input, re.I) for p in CRISIS_CHECKIN_PATTERNS)


def semantic_distress_check(user_input: str):
    """OPTIONAL L2-style hook on the INPUT (mirrors v3's semantic_intent_check, which judges
    OUTPUT). Oblique distress that evades BOTH pattern tiers can get one semantic look here if
    an integrator wires an LLM classifier. Defaults to None = "NOT ASSESSED" (stdlib-only, no
    model call at import — L1 stays import-clean). Wire by reassigning this name to a real
    classifier: returns True (distress), False (clear), or None (not assessed / abstain)."""
    return None


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


def gate(user_input: str, candidate_output: str, citations: list, locale=None) -> dict:
    """citations: list of (quote, ref) tuples the candidate_output relies on.
    locale: optional ISO-ish locale ('kr','us','gb', ...) for the crisis resource; None ->
    answer in the input's language (English base, Korean compatible)."""
    # (2a) CRISIS-OVERRIDE — HIGH-CONFIDENCE (Tier 1). Highest precedence; overrides comfort +
    #      no-trace destruction. Also fires if a wired semantic INPUT hook returns True.
    sem = semantic_distress_check(user_input)
    if detect_crisis(user_input) or sem is True:
        return {
            "verdict": "CRISIS_OVERRIDE",
            "output": crisis_response(locale, user_input=user_input),
            "actions": ["escalate_to_human", "preserve_record (override Vault destruction)"],
            "note": "safety > comfort; 'total acceptance' architecture suspended"
                    + ("; semantic-input-hook" if sem is True and not detect_crisis(user_input) else ""),
        }
    # (2b) CRISIS-CHECKIN — LOW-THRESHOLD (Tier 2). Oblique hopelessness/anhedonia/worthlessness/
    #      burden routes to a GENTLE check-in + resource INSTEAD of straight comfort. Over-triggers
    #      on purpose (false positive = a kind question; false negative = a missed crisis = worst).
    if detect_checkin(user_input):
        return {
            "verdict": "CRISIS_CHECKIN",
            "output": crisis_checkin(locale, user_input=user_input),
            "actions": ["gentle_checkin", "offer_resource", "do_not_paper_over_with_comfort"],
            "note": "low-confidence oblique distress; softer than Tier-1, still NOT blank comfort",
        }
    # (1) SCRIPTURE-GROUNDING, FAIL-CLOSED — every cited verse must match the verified DB.
    ungrounded = [ref for (quote, ref) in citations if not scripture_grounded(quote, ref)]
    if ungrounded:
        return {
            "verdict": "FAIL_CLOSED",
            "output": (
                "(검증된 성구를 찾지 못해 성구 인용을 중단합니다. 임의 생성하지 않습니다.)"
                if _has_korean(user_input)
                else "(No verified scripture match found — halting the quotation. Nothing is fabricated.)"
            ),
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
