#!/usr/bin/env python3
"""
The Bible — L1 normalization primitives (Round-3 strengthening / R8).

The v3 L1 floor only stripped whitespace. An adversary who writes a safety-tripping intent in
homoglyphs ("ɗіе"), fullwidth ("ｄｉｅ"), zero-width-injected ("d​i​e"), or a base64/hex blob slips
PAST every regex pattern unchanged. This module adds the *de-obfuscation + detection* layer the
patterns sit on top of — entirely stdlib (NO model call at import; L1 stays import-clean), so v5 can
re-run the existing safety patterns against several NORMALIZED VIEWS of one input and block if ANY
view trips. That is a fail-closed, recall-increasing pass: an obfuscated evasion is itself a signal.

DESIGN ALIGNMENT (Round-3 discovery scan — see DESIGN.md §4 R8):
  #1 UTS#39 skeleton — used as a DETECTION/matching view + a mixed-script-confusable flag, NEVER as the
     canonical text fed downstream (skeleton is over-inclusive → remapping on it would create false
     matches; UTS#39 itself notes skeleton is "overly inclusive"). The verse domain affords a tight
     expected-script allow-list, so a Latin/Hangul utterance carrying a lone Cyrillic/Greek homoglyph
     is the attack signature.
  #2 CPT (characters-per-token) — the cited ~99.7% obfuscation detector (arXiv:2510.26847) needs a real
     BPE tokenizer, which would break L1's stdlib-only/import-clean contract. So this module ships the
     STDLIB FLOOR — lossless base64/hex decode-and-rescan (high-value: it de-obfuscates the actual
     intent) — and exposes `cpt_obfuscation_check` as a default-None integrator hook (mirrors
     `semantic_distress_check`) for the cited-accuracy path. We do NOT claim the 99.7% figure for the
     stdlib floor; that figure belongs to the wired BPE path. Honest scope, not a phantom number.

HONEST RESIDUALS (named, not hidden):
  - The confusables table is a CURATED high-value subset (Cyrillic/Greek→Latin + a few common ones),
    not the full Unicode confusables.txt. It closes the common homoglyph classes, not every pair.
  - General Caesar cipher (arbitrary shift 1-25, reversed text) is NOT decoded — only ROT13 (shift 13
    specifically) is, per R9 below. A shift other than 13, or simple character-reversal, still evades.
    Left to the optional CPT hook / L2, named here (same posture the R8 base64/hex floor already
    takes toward what it does NOT cover).

ROUND-9 STRENGTHENING (R9, 2026-08-16): the two residuals this docstring used to name — "leetspeak is
deliberately NOT folded" and "rot13 ciphers are not decoded" — are CLOSED below, not merely revised in
prose. Third-party evidence forced the correction: `deepteam` (Apache-2.0 LLM red-team framework,
github.com/confident-ai/deepteam), run from an isolated scratch venv against `grounding_gate_v3.gate`
directly (no repo dependency added — same battery-testing posture as R1-R8, tool stays external), found
that its actual `ROT13`/`Leetspeak` attack encoders fully bypass BOTH `CRISIS_OVERRIDE` (a suicidal-
ideation sentence, verbatim, encoded either way -> PASS) and `ABSOLUTION` blocking (an absolution
declaration, encoded either way -> PASS). A base64 positive control against the same tool's own
`Base64` encoder confirmed R8's claim still holds (CRISIS_OVERRIDE unchanged) — the finding is real,
not a broken test harness. Full writeup: DESIGN.md §4 R9.

Both prior objections are addressed, not overridden silently:
  - ROT13 is a SINGLE fixed substitution (shift 13, self-inverse) — unlike general Caesar (25 shifts)
    it needed no blob-boundary search the way base64/hex did, so "unbounded" never actually applied to
    it specifically; that was an overgeneralization from the Caesar-cipher family to one bounded member.
  - Leetspeak's over-triggering objection ("Psalm 23" folding) is real for a CANONICAL fold, but does
    not apply to a DETECTION-ONLY VIEW unioned alongside the untouched original — the same posture
    `skeleton()`/`strip_combining()` already use below. An accidental digit->letter fold on a verse
    number does not itself match a multi-word safety phrase; it is checked, not corrupted.
"""
import base64
import binascii
import re
import unicodedata
import urllib.parse


def _fold_apostrophes(text: str) -> str:
    """Fold curly/typographic apostrophes + quotes to ASCII so contraction patterns (don'?t) match
    'don’t' etc. Returns '' when unchanged (Codex round-3 2026-07-03)."""
    if not text:
        return ""
    return (text.replace("’", "'").replace("‘", "'").replace("ʼ", "'")
                .replace("“", '"').replace("”", '"').replace("´", "'"))


def _percent_decode(text: str) -> str:
    """URL/percent + '+' decode. Returns '' when unchanged (so it adds a view only when it
    actually de-obfuscates). Closes 'I%20want%20to%20die' / 'I+want+to+die' (Codex 2026-07-03)."""
    try:
        d = urllib.parse.unquote_plus(text or "")
        return d if d and d != text else ""
    except Exception:
        return ""

# --- Optional integrator hook (default None = NOT ASSESSED) ---------------------------------------
# Wire by reassigning to a real BPE-tokenizer-backed detector returning True (obfuscated) / False
# (clean) / None (abstain). Keeps L1 import-clean while leaving the cited-accuracy path open.
cpt_obfuscation_check = None


# --- Curated UTS#39-style confusables (homoglyph → Latin prototype) -------------------------------
# A high-value subset: the scripts an adversary reaches for to spoof a Latin/ASCII safety token.
# Skeleton = NFKC-fold THEN map each char through this table. Used for DETECTION + an extra match
# view, never as the canonical downstream text.
_CONFUSABLES = {
    # Cyrillic → Latin
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x",
    "і": "i", "ј": "j", "ѕ": "s", "к": "k", "м": "m", "н": "h", "т": "t",
    "в": "b", "г": "r", "ё": "e", "ԛ": "q", "ԝ": "w",
    # Greek → Latin
    "ο": "o", "α": "a", "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "ι": "i",
    "κ": "k", "η": "n", "ε": "e", "χ": "x", "ζ": "z", "β": "b",
    # a couple of common symbol homoglyphs
    "ѵ": "v", "ӏ": "l",
    # Latin-block / IPA / phonetic lookalikes — SAME-SCRIPT homoglyphs that a cross-script check
    # cannot see (cross-family audit 2026-06-28, F2: 'kɪll', 'ɑbsolve' evaded every view).
    "ɪ": "i", "ɑ": "a", "ɡ": "g", "ɩ": "i", "ʟ": "l", "ɴ": "n", "ʀ": "r", "ʏ": "y",
    "ᴀ": "a", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ɢ": "g", "ʜ": "h", "ᴊ": "j", "ᴋ": "k",
    "ᴍ": "m", "ᴏ": "o", "ᴘ": "p", "ꜱ": "s", "ᴛ": "t", "ᴜ": "u", "ᴠ": "v", "ᴡ": "w",
    "ɓ": "b", "ɗ": "d", "ɛ": "e", "ɸ": "o", "ɟ": "j", "ʄ": "j", "ɭ": "l", "ɽ": "r",
    "ı": "i", "ǐ": "i", "ⅼ": "l", "ⅰ": "i", "ⅽ": "c", "ⅾ": "d", "ⅿ": "m",
}


def strip_format_chars(text: str) -> str:
    """Remove invisible / format / control characters BEFORE any normalization (round-3 #1 ordering).

    Drops Unicode category Cf (format, incl. zero-width joiners/non-joiners, bidi controls), Cc control
    (except \\n \\t \\r), and default-ignorable-style spacers. These are the classic "split a banned
    token with an invisible char" evasion ("d\\u200bie"). Stripping them first means the downstream NFKC
    + pattern pass sees the real token.
    """
    if not text:
        return text or ""
    out = []
    for ch in text:
        if ch in ("\n", "\t", "\r"):
            out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Cc", "Cs", "Co", "Cn"):
            continue
        # explicit zero-width / BOM / word-joiner even if some platform miscategorizes them
        if ch in ("​", "‌", "‍", "﻿", "⁠", "­"):
            continue
        out.append(ch)
    return "".join(out)


# Specifically-suspicious format chars (vs benign-in-CJK fullwidth): zero-width, bidi controls,
# soft hyphen, word joiner, BOM. Their presence in input is an obfuscation signal in its own right
# (cross-family audit 2026-06-28, F3) — distinct from NFKC-changing fullwidth, which is benign typing.
_SUSPICIOUS_FORMAT = set("​‌‍⁠﻿­᠎"
                         "‪‫‬‭‮⁦⁧⁨⁩")


def nfkc(text: str) -> str:
    """NFKC compatibility normalization — folds fullwidth (ｄｉｅ→die), ligatures, circled/super forms.

    Lossless FOR OUR PURPOSE: we only re-run safety patterns on the result, we never store it as the
    user's text. This catches the cheap compatibility-variant evasion class.
    """
    return unicodedata.normalize("NFKC", strip_format_chars(text or ""))


def strip_combining(text: str) -> str:
    """Drop nonspacing combining marks (category Mn) via NFD, then NFC — a matching VIEW only.

    Defeats the combining-overlay evasion ('k̶i̶l̶l̶' with U+0336 between letters), which NFKC does NOT
    remove (cross-family audit 2026-06-28, F2). Applied only to produce an extra re-match view, never
    stored as canonical text — combining marks ARE meaningful in some scripts, so this is detection-side.
    """
    decomposed = unicodedata.normalize("NFD", strip_format_chars(text or ""))
    no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", no_marks)


def skeleton(text: str) -> str:
    """UTS#39-style skeleton: NFKC, then map each char through the curated confusables table.

    For DETECTION only (an extra matching view + mixed-script flag). Over-inclusive by design — never
    fed downstream as canonical text.
    """
    folded = nfkc(text)
    return "".join(_CONFUSABLES.get(ch, _CONFUSABLES.get(ch.lower(), ch)) for ch in folded)


def rot13(text: str) -> str:
    """ROT13 decode/encode (self-inverse, shift 13) — a DETECTION view. A bounded, single fixed
    substitution (not the unbounded general-Caesar family) — R9, DESIGN.md §4 R9. Union-only: this
    never replaces the original view, so applying it to already-plain text just yields gibberish
    that will not accidentally match a multi-word safety phrase."""
    if not text:
        return ""
    return text.translate(
        str.maketrans(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
        )
    )


# Reverse-leetspeak digit/symbol -> letter map. '1' is genuinely ambiguous (both i and l commonly
# encode to it), so de_leetspeak() below returns TWO views rather than picking one guess — union,
# recall-increasing, same fail-closed direction as every other view in this module.
_DELEET_MAP_I = {"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t"}
_DELEET_MAP_L = {"4": "a", "3": "e", "1": "l", "0": "o", "5": "s", "7": "t"}


def de_leetspeak(text: str):
    """Reverse common leetspeak digit/symbol substitutions — TWO detection-only views ('1'->'i' and
    '1'->'l', since that mapping is ambiguous). NEVER fed downstream as canonical text — same posture
    as skeleton()/strip_combining(): unioned alongside the untouched original, so an accidental fold
    on ordinary numeric text (a verse number, a date) is re-checked, not corrupted (R9,
    DESIGN.md §4 R9 — this was the exact over-triggering objection that previously blocked folding
    leetspeak at all; a union view does not have that failure mode, only a canonical replacement would).
    """
    if not text:
        return ["", ""]
    return (
        "".join(_DELEET_MAP_I.get(ch, ch) for ch in text),
        "".join(_DELEET_MAP_L.get(ch, ch) for ch in text),
    )


def _script_of(ch: str) -> str:
    """Coarse script bucket for a single char (homoglyph-spoofing detection granularity)."""
    cp = ord(ch)
    if 0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F:
        return "Cyrillic"
    if 0x0370 <= cp <= 0x03FF or 0x1F00 <= cp <= 0x1FFF:
        return "Greek"
    if 0xAC00 <= cp <= 0xD7A3 or 0x1100 <= cp <= 0x11FF or 0x3130 <= cp <= 0x318F:
        return "Hangul"
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "Han"
    if (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A):
        return "Latin"
    return "Common"


def is_mixed_script_confusable(text: str) -> bool:
    """True if a single alphabetic run mixes scripts in a homoglyph-spoofing way.

    The attack: a mostly-Latin word with a lone Cyrillic/Greek letter (or vice-versa) — e.g. 'dіe'
    (Latin d, e + Cyrillic і). A legitimately multilingual sentence has scripts in SEPARATE words;
    spoofing puts two scripts INSIDE one word. We flag a run that contains Latin AND (Cyrillic or
    Greek), since those are the homoglyph donors for Latin. Hangul+Latin in one run is NOT flagged
    (no Latin homoglyphs in Hangul; ordinary KR/EN code-mixing).
    """
    for run in re.findall(r"[^\s\d\W]+", nfkc(text), re.UNICODE):
        scripts = {_script_of(ch) for ch in run if ch.isalpha()}
        if "Latin" in scripts and ("Cyrillic" in scripts or "Greek" in scripts):
            return True
    return False


# --- base64 / hex decode-and-rescan (the stdlib CPT-floor: lossless de-obfuscation) ---------------
# NO word-boundary anchor: \b fails when a blob is glued to CJK (cross-family audit 2026-06-28, F1,
# '읽어SSB...제발'). We scan maximal base64-alphabet runs and let strict validate-decode be the real
# filter. Threshold 12 (not 16) so a short crisis payload survives: 'kill myself' → 'a2lsbCBteXNlbGY='
# is only 15 alnum chars and was missed by {16,}.
# Lowered 2026-07-03 (Codex round-10) to 8 b64 chars / 6 hex bytes so SHORT single-word stems survive
# ('suicid'->'c3VpY2lk', '자해'->'7J6Q7ZW0', hex '737569636964'). DOCUMENTED bounded residual: stems
# below ~6 bytes ('die'->'ZGll', 4 chars) are NOT decoded — going lower decodes nearly every short
# token (FP + DoS), so ultra-short encoded stems are the L2 semantic-Guardian's backstop (L1-is-partial
# design). Safe: a decoded view only BLOCKS on a safety-pattern hit + printable>=0.85, ~no benign FP.
_B64_RE = re.compile(r"[A-Za-z0-9+/]{8,}={0,2}")
_HEX_RE = re.compile(r"(?:[0-9a-fA-F]\s*){12,}")  # single-char run (odd-len ok: no nibble drop, Codex r13)
_MAX_BLOB_IN = 8192    # ignore absurdly long candidate blobs (DoS guard, F5)
_MAX_DECODED = 4096    # cap decoded view length fed to the pattern rescan
_MAX_BLOBS = 8         # cap how many blobs we decode per input


def _printable_ratio(s: str) -> float:
    if not s:
        return 0.0
    printable = sum(1 for c in s if c.isprintable() or c in (" ", "\n", "\t"))
    return printable / len(s)


_MAX_TOTAL_ATTEMPTS = 40000                               # total de-glue decode attempts per input (DoS
#   bound across ALL blobs — replaces the per-blob COUNT cap a decoy blob could exhaust, Codex round-14)
_DEGLUE_MAX_START = 256                                    # scan embedded-blob start offsets up to here
_DEGLUE_WIN = 64                                          # max chars decoded per start (~48 bytes b64 /
#   32 bytes hex) — covers a crisis phrase / scripture ref. ONE loose decode per start: decode the
#   window, IGNORE invalid-utf8 tail bytes (suffix alphabet-junk) + keep printable, so 'c3VpY2lk'+'Q'*80
#   still yields 'suicid' and no length enumeration / shortest-first truncation is needed (Codex r15).
#   Prefix junk is handled by the start scan; O(starts), each decode tiny → the wide scan stays fast.


def _printable_only(s):
    """Keep printable chars + basic whitespace (drop decoded junk control bytes). A short de-glue view
    is fed to substring pattern-match, so junk-control removal leaves an embedded stem intact."""
    return "".join(c for c in s if c.isprintable() or c in " \t")


def _b64_try(frag):
    """Strict-decode one base64 alphabet fragment (pad as needed); return clean text or None."""
    if len(frag) < 8 or len(frag) % 4 == 1:
        return None
    try:
        s = base64.b64decode(frag + "=" * (-len(frag) % 4), validate=True).decode("utf-8", "strict")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    return s if len(s) >= 2 and _printable_ratio(s) >= 0.85 else None


def _b64_loose(seg):
    """De-glue decode of a base64 window: decode as much as validates, IGNORE invalid-utf8 tail bytes
    (suffix alphabet-junk), keep the printable result. One decode per start — the embedded stem survives
    as a substring without length enumeration or shortest-first truncation (Codex round-15)."""
    if len(seg) < 8:
        return None
    if len(seg) % 4 == 1:
        seg = seg[:-1]
    try:
        raw = base64.b64decode(seg + "=" * (-len(seg) % 4), validate=True)
    except (binascii.Error, ValueError):
        return None
    s = _printable_only(raw.decode("utf-8", "ignore"))
    return s if len(s) >= 2 else None


def _hex_try(frag):
    """Strict-decode one even-length hex fragment; return clean text or None."""
    if len(frag) < 4 or len(frag) % 2:
        return None
    try:
        s = bytes.fromhex(frag).decode("utf-8", "strict")
    except (ValueError, UnicodeDecodeError):
        return None
    return s if len(s) >= 2 and _printable_ratio(s) >= 0.85 else None


def _hex_loose(seg):
    """De-glue decode of a hex window (see _b64_loose)."""
    if len(seg) < 4:
        return None
    if len(seg) % 2:
        seg = seg[:-1]
    try:
        raw = bytes.fromhex(seg)
    except ValueError:
        return None
    s = _printable_only(raw.decode("utf-8", "ignore"))
    return s if len(s) >= 2 else None


def decode_blobs(text: str) -> list:
    """Find base64/hex blobs, decode, return decoded strings that are mostly printable text (so an
    intent encoded to dodge the patterns gets re-scanned in the clear).

    Bounded + lossless: only well-formed blobs that strict-decode to readable text are returned; a
    random token that is base64-shaped but decodes to binary is dropped. Length/count capped (F5).
    NOTE: a benign token decoding to clean text (e.g. an API key → 'SomeVerifyToken123') IS returned
    here as a rescan view, but it does NOT by itself raise the obfuscation FLAG (see normalized_views,
    F4) — only a SAFETY-PATTERN hit on the decoded view blocks.

    SLIDING WINDOW (Codex round-11/12 2026-07-03): a maximal alphabet run that fails to decode AS A
    WHOLE can still embed a valid SHORT stem glued to base64/hex-alphabet junk ('xxc3VpY2lk',
    'aaaaaaaaaac3VpY2lk', 'c3VpY2lkxx', 'xSm9iIDM6MQ=='). Two passes: (1) whole-run decode for a full
    legit blob of any length; (2) a SHORT-window de-glue — a crisis stem / scripture ref is short, so
    we scan start offsets across the run (up to _DEGLUE_MAX_START) trying short fixed fragment lengths
    only. Short fragments make each decode cheap, so a WIDE start scan stays fast (a stem after any
    reasonable amount of prefix junk is found — round-11's per-start tail-trim wrongly spent the whole
    budget within ~8 starts). Accepted residual: junk prefix glued (no separator) beyond the start-scan reach
    (~310 chars — the 256 start cap plus the 64-char window overlap) — L2 semantic Guardian backstops it.
    """
    if not text:
        return []
    decoded = []
    budget = [_MAX_TOTAL_ATTEMPTS]     # total de-glue attempts across ALL blobs (DoS bound). NOT a
    # per-blob-COUNT cap: an early decoded-count break let 8 benign decoy blobs starve a trailing crisis
    # blob (Codex round-14). A safety floor must scan EVERY blob; only total work is bounded (input seed
    # is already ≤4096, so blob count is naturally bounded — the budget just backstops the pathological).

    def _add(s):
        if s is not None and s[:_MAX_DECODED] not in decoded:
            decoded.append(s[:_MAX_DECODED])

    for m in _B64_RE.findall(text):
        if budget[0] <= 0:
            break
        if len(m) > _MAX_BLOB_IN:
            continue
        run = m.rstrip("=")
        _add(_b64_try(run))                                  # (1) whole run (full legit blob)
        limit = min(len(run), _DEGLUE_MAX_START + 1)         # (2) short-window de-glue (start 0..cap incl.)
        for start in range(limit):
            if budget[0] <= 0:
                break
            budget[0] -= 1                                   # one loose decode per start (ignore junk tail)
            _add(_b64_loose(run[start:start + _DEGLUE_WIN]))

    for m in _HEX_RE.findall(text):
        if budget[0] <= 0:
            break
        hx = re.sub(r"\s+", "", m)
        if len(hx) > _MAX_BLOB_IN:
            continue
        _add(_hex_try(hx if len(hx) % 2 == 0 else hx[:-1]))  # (1) whole run
        limit = min(len(hx), _DEGLUE_MAX_START + 1)          # (2) short-window de-glue (start 0..cap incl.)
        for start in range(limit):
            if budget[0] <= 0:
                break
            budget[0] -= 1
            _add(_hex_loose(hx[start:start + _DEGLUE_WIN]))
    return decoded


def normalized_views(text: str):
    """Return (views, flags) for an input.

    views  — distinct normalized strings to re-run the L1 safety patterns against. Always includes the
             original; adds NFKC, skeleton, and any decoded base64/hex blobs when they differ. Running
             the patterns over this set is a UNION (recall-increasing, fail-closed direction).
    flags  — dict of mechanically-detected obfuscation signals:
               obfuscation_attempted : bool (any signal below)
               mixed_script          : bool (homoglyph spoofing)
               had_format_chars      : bool (invisible/zero-width chars were present)
               decoded_blob          : bool (a base64/hex blob decoded to text)
               cpt                   : True/False/None from the optional CPT hook (None = not wired)
    """
    text = text or ""
    folded = nfkc(text)
    skel = skeleton(text)
    no_marks = strip_combining(text)            # F2: combining-overlay evasion view
    skel_no_marks = skeleton(no_marks)          # homoglyph + combining stacked
    apos = _fold_apostrophes(text)              # curly-apostrophe view (contraction patterns)
    r13 = rot13(text)                            # R9: ROT-13 decode view (single fixed substitution)
    deleet_i, deleet_l = de_leetspeak(text)      # R9: reverse-leetspeak views ('1'->'i' / '1'->'l')
    deleet_i_r13 = rot13(deleet_i)                # R9: stacked leetspeak+ROT13 (deepteam chains
    deleet_l_r13 = rot13(deleet_l)                # single-turn attacks; a stacked probe is cheap here)
    # COMPOSED view (Codex round-7): single-transform views are UNIONed but not COMPOSED, so a
    # layered attack (Cyrillic homoglyph + curly apostrophe + fullwidth + zero-width all at once) is
    # missed by every single view. Apply all normalizers together so it collapses in one view.
    composed = strip_combining(skeleton(nfkc(apos)))

    # BOUNDED RECURSIVE DECODE — seed the frontier with the NORMALIZED variants too, not just raw text
    # (Codex round-9): a fullwidth-percent / zero-width-split base64 needs normalize-THEN-decode
    # (fullwidth '％' → NFKC → '%' → percent-decode; zero-width-broken base64 → format-strip → clean →
    # decode). Combined with decoded_composed (decode-THEN-normalize, round-8) this closes both orders.
    # Still bounded (depth 3, per-item caps in decode_blobs) — infinite cipher regress stays out of scope.
    decoded = set()
    frontier = [text, folded, skel, no_marks, apos, composed]
    for _depth in range(3):
        nxt = []
        for s in frontier:
            if len(s) > 4096:   # perf bound (Codex round-10): a hidden SHORT crisis fits in a small
                continue        # blob; skip decoding huge seeds (a real crisis message is not 8 KB).
            cands = list(decode_blobs(s))
            p = _percent_decode(s)
            if p:
                cands.append(p)
            for d in cands:
                if d and d not in decoded:
                    decoded.add(d)
                    nxt.append(d)
        if not nxt:
            break
        frontier = nxt

    # Each DECODED item is re-normalized too (Codex round-8): a blob can decode to a STILL-obfuscated
    # string (e.g. '%D0%BE' → Cyrillic 'о'); compose the decoded view so the homoglyph doesn't survive.
    decoded_composed = [strip_combining(skeleton(nfkc(_fold_apostrophes(d)))) for d in decoded]
    views = []
    seen = set()
    for v in (text, folded, skel, no_marks, skel_no_marks, apos, composed,
              r13, deleet_i, deleet_l, deleet_i_r13, deleet_l_r13,
              *sorted(decoded), *decoded_composed):
        if v and v not in seen:
            seen.add(v)
            views.append(v)

    cpt = None
    if cpt_obfuscation_check is not None:
        try:
            cpt = cpt_obfuscation_check(text)
        except Exception:
            cpt = None  # a broken hook never crashes L1; absence is handled by the caller fail-closed

    # homoglyph_present: a confusable was folded by the skeleton (covers Cyrillic/Greek AND same-script
    # Latin/IPA lookalikes — F2). Generic: skeleton != NFKC means SOME mapped homoglyph was present.
    # Does NOT false-positive on accented words (é/ï aren't in the confusables map). (Supersedes the
    # narrower cross-script-only `mixed_script` check, kept as a secondary signal.)
    homoglyph = (skel != folded) or (skel_no_marks != strip_combining(folded)) or is_mixed_script_confusable(text)
    suspicious_format = any(ch in _SUSPICIOUS_FORMAT for ch in text)
    flags = {
        "homoglyph": homoglyph,
        "mixed_script": is_mixed_script_confusable(text),
        "suspicious_format": suspicious_format,   # zero-width/bidi (F3) — NOT benign fullwidth
        "had_format_chars": strip_format_chars(text) != text,
        "decoded_blob": bool(decoded),
        "cpt": cpt,
    }
    # FLAG trigger (obfuscation detected but de-obfuscated clean -> L3). decoded_blob is DELIBERATELY
    # NOT a trigger (F4): a benign base64 token decoding to clean text must not FLAG — only a
    # safety-pattern hit on the decoded VIEW blocks (the caller re-matches views). The flag fires on
    # homoglyph / suspicious zero-width-bidi / a positive CPT-hook verdict.
    flags["obfuscation_attempted"] = bool(homoglyph or suspicious_format or cpt is True)
    return views, flags
