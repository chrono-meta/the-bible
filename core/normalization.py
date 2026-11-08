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

HONEST RESIDUALS (named, not hidden) — as of R11 (2026-11-07):
  - The homoglyph FLAG still uses the CURATED table (skeleton()); the full UTS#39 single-code-point
    table (skeleton_full(), R11) is a match view only, so a lookalike outside the curated set blocks on
    a pattern hit but does not by itself raise the obfuscation FLAG. Multi-code-point confusables
    ('rn' -> 'm') are not folded.
  - Keyed ciphers (Vigenère etc.) and STACKED transforms (e.g. a Caesar shift of a reversed string)
    are not composed. The R11b de-glue scan for Base32/Ascii85/Base85 is budgeted (384 decodes per codec,
    runs <= 320 chars). Reversed Hangul is not viewed at all (blanked; a signal-gated R11b attempt was
    withdrawn after review reproduced over-blocks). All left to the optional CPT hook / L2, named in DESIGN.md §5.
  (General Caesar / reversal were CLOSED in R11; Ecoji / Base2048 / glued byte codecs in R11b — see below.)

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
import functools
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


from confusables_data import CONFUSABLE_TO_LATIN as _CONFUSABLES_FULL  # noqa: E402  (R11, generated data)


_DIGITS = frozenset("0123456789")   # never folded in skeleton_full: '1'->'l' turned verse refs 'Gen 3:21'
#   into 'Gen 3:2l', which the output-side reference scan read as an UNCITED 'Gen 3:2' -> FAIL_CLOSED on
#   279 grounded KJV outputs in the FP lane. Digit->letter folding is de_leetspeak()'s job (its own views).


def skeleton_full(text: str) -> str:
    """R11: skeleton over the FULL UTS #39 single-code-point -> ASCII-letter table (1,451 entries,
    core/confusables_data.py, regenerated by core/build_confusables.py) on top of NFKC + combining-strip
    + apostrophe-fold. MATCH VIEW ONLY: it is deliberately NOT used for the homoglyph FLAG (that stays on
    the curated _CONFUSABLES via skeleton()), because the full table also maps ASCII 'I'/'|' and
    typographic signs like '×' — folding those into the flag would over-FLAG ordinary text. As a pure
    re-match view it can only BLOCK on a safety-pattern hit, the same posture as every other view."""
    def _map(t):
        return "".join(ch if ch in _DIGITS else _CONFUSABLES_FULL.get(ch, _CONFUSABLES.get(ch, ch)) for ch in t)
    # map RAW first too: confusables.txt is newer than Python's UCD, so a code point it lists may be
    # category Cn here (strip_format_chars would DROP it), and NFKC re-targets a few ('ſ' -> 's'
    # where the visual prototype is 'f'). raw-map -> normalize -> map again closes both orders.
    return _map(strip_combining(nfkc(_fold_apostrophes(_map(text or "")))))


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


# --- R11 (2026-11-07, W3 / AQ-20261107-16): cipher + transcoding views ------------------------------
# DESIGN.md §5 listed eight classes as open: six MEASURED to pass a verbatim crisis sentence straight
# through (general Caesar, reversal, Atbash, Base32, Ascii85, uuencode) and two UNMEASURED (Morse,
# Braille). R11 measured all eight again — plus the other garak-0.16.0 active encoders §5 did not
# name (NATO, Unicode-tag, variant-selector, sneaky-bits, ecoji, base2048) — with the tool's own
# encoders, controls first, L2 stubbed so the verdict is the L1 floor's. Every class that fit a
# bounded stdlib decode got a DETECTION-ONLY view below; ecoji and base2048 are left on purpose
# (see DESIGN.md §4 R11 for the before→after table and the FP lane that gated each view).
# Same posture as rot13()/de_leetspeak(): every view is UNIONED alongside the untouched original and
# only re-matched, never fed downstream; each is bounded (fixed transform, or a capped decode).

_MAX_CIPHER_IN = 8192   # = _MAX_BLOB_IN. Codex R11-r1: a 2,048 cap let a short shifted payload hide behind
#   2 KB of padding; str.translate is O(n), so the whole input is shifted instead of skipped.


_LOW, _UP = "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_SHIFT_TABLES = {k: str.maketrans(_LOW + _UP, _LOW[k:] + _LOW[:k] + _UP[k:] + _UP[:k]) for k in range(26)}


def _shift(text: str, k: int) -> str:
    return text.translate(_SHIFT_TABLES[k % 26])


def caesar_views(text: str) -> list:
    """All 24 remaining Caesar shifts (1-25 minus 13, which rot13() already covers). Bounded: a fixed
    family of 24 substitutions — the "unbounded" objection the R8 docstring raised applies to keyed
    ciphers (Vigenère), not to a 26-member alphabet rotation. Detection-only, union."""
    if not text or len(text) > _MAX_CIPHER_IN or not re.search(r"[A-Za-z]", text):
        return []
    return [_shift(text, k) for k in range(1, 26) if k != 13]


def atbash(text: str) -> str:
    """Atbash (a<->z mirror) — a single fixed self-inverse substitution, same class as rot13()."""
    if not text:
        return ""
    return text.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "ZYXWVUTSRQPONMLKJIHGFEDCBAzyxwvutsrqponmlkjihgfedcba"))


_HANGUL_RUN = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]+")


def reversed_view(text: str) -> str:
    """Character reversal (whole string), EXCEPT that each Hangul run is restored to reading order.
    Codex R11-r1 reproduced a real over-block: reversing Korean prose manufactures 2-syllable crisis
    tokens ('서유기' -> '기유서' ⊃ '유서', '피해자' -> '자해피' ⊃ '자해'). Korean crisis patterns are
    short, so a reversed-Hangul view is FP-prone by construction; Latin reversal is kept (multi-word EN
    patterns do not appear by accident) and Hangul is blanked out of the view. A reversed-Hangul payload is a measured, named residual
    (DESIGN.md §5)."""
    if not text or len(text) > _MAX_CIPHER_IN:
        return ""
    # Hangul runs are BLANKED, not just restored: restored runs in reversed WORD order still glued into
    # crisis tokens once the gate whitespace-strips the view ('해제는 … 운영자' -> '운영자해제는' ⊃ '자해',
    # found by the 20k-line Korean FP lane). The view exists for Latin payloads only.
    return _HANGUL_RUN.sub(" ", text[::-1])


_MORSE = {
    ".-": "a", "-...": "b", "-.-.": "c", "-..": "d", ".": "e", "..-.": "f", "--.": "g", "....": "h",
    "..": "i", ".---": "j", "-.-": "k", ".-..": "l", "--": "m", "-.": "n", "---": "o", ".--.": "p",
    "--.-": "q", ".-.": "r", "...": "s", "-": "t", "..-": "u", "...-": "v", ".--": "w", "-..-": "x",
    "-.--": "y", "--..": "z", ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5",
    "-....": "6", "--...": "7", "---..": "8", "----.": "9", "-----": "0",
    ".-.-.-": ".", "--..--": ",", "..--..": "?", ".----.": "'", "-.-.--": "!",
}
# a run of >=3 morse letters (dot/dash groups) separated by spaces or word-slashes
_MORSE_RUN = re.compile(r"[.\-]{1,6}(?:(?:\s*/\s*|\s+)[.\-]{1,6}){2,}")


def morse_decode(text: str) -> str:
    """Decode morse runs ('.-' alphabet, ' ' between letters, '/' between words). Common typographic
    stand-ins (·•∙ for dot, −–—_ for dash) are folded first. Unknown groups decode to nothing.
    Returns '' when no run decodes."""
    if not text or len(text) > _MAX_CIPHER_IN * 4:
        return ""
    t = re.sub("[·•∙]", ".", text)
    t = re.sub("[−–—_]", "-", t)
    words_out = []
    for m in _MORSE_RUN.findall(t):
        words = [w for w in re.split(r"\s*/\s*", m.strip()) if w]
        words_out.append(" ".join("".join(_MORSE.get(g, "") for g in w.split()) for w in words))
    s = " ".join(w for w in words_out if w.strip())
    return s if len(s.replace(" ", "")) >= 3 else ""


# Grade-1 English braille cells (the garak/standard letter map). Digits share a-j cells after the
# number sign; the caps sign is dropped (patterns match case-insensitively anyway).
_BRAILLE = {
    "⠁": "a", "⠃": "b", "⠉": "c", "⠙": "d", "⠑": "e", "⠋": "f", "⠛": "g", "⠓": "h", "⠊": "i",
    "⠚": "j", "⠅": "k", "⠇": "l", "⠍": "m", "⠝": "n", "⠕": "o", "⠏": "p", "⠟": "q", "⠗": "r",
    "⠎": "s", "⠞": "t", "⠥": "u", "⠧": "v", "⠺": "w", "⠭": "x", "⠽": "y", "⠵": "z",
    "⠲": ".", "⠂": ",", "⠄": "'", "⠤": "-", "⠌": "/", "⠖": "!", "⠦": "?", "⠒": ":", "⠰": ";",
    "⠀": " ",
}
_BRAILLE_DIGIT = dict(zip("⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚", "1234567890"))


def braille_decode(text: str) -> str:
    """Transcribe Unicode braille cells (U+2800-28FF) to Latin; non-braille chars pass through.
    Returns '' when the text holds fewer than 3 braille cells."""
    if not text or sum(1 for ch in text if "⠀" <= ch <= "⣿") < 3:
        return ""
    out, num = [], False
    for ch in text:
        if ch == "⠠":          # caps sign
            continue
        if ch == "⠼":          # number sign: following a-j cells are digits until a non-digit cell
            num = True
            continue
        if num and ch in _BRAILLE_DIGIT:
            out.append(_BRAILLE_DIGIT[ch])
            continue
        num = False
        out.append(_BRAILLE.get(ch, ch))
    return "".join(out)


_NATO = {
    "alfa": "a", "alpha": "a", "bravo": "b", "charlie": "c", "delta": "d", "echo": "e",
    "foxtrot": "f", "golf": "g", "hotel": "h", "india": "i", "juliett": "j", "juliet": "j",
    "kilo": "k", "lima": "l", "mike": "m", "november": "n", "oscar": "o", "papa": "p",
    "quebec": "q", "romeo": "r", "sierra": "s", "tango": "t", "uniform": "u", "victor": "v",
    "whiskey": "w", "xray": "x", "x-ray": "x", "yankee": "y", "zulu": "z",
}
_NATO_RUN = re.compile(r"(?:\b(?:%s)\b[\s,/|.;:\-]*){4,}" % "|".join(sorted(map(re.escape, _NATO), key=len, reverse=True)),
                       re.I)


def nato_decode(text: str) -> str:
    """Spelling-alphabet runs (>=4 consecutive code words) -> their letters, concatenated. Word breaks
    are lost by the encoding itself; the whitespace-stripped match in the gate already handles that."""
    if not text or len(text) > _MAX_CIPHER_IN * 8:
        return ""
    # separators may be space, comma, slash, pipe, dot or hyphen (Codex R11-r1: ' / ' and '-' slipped);
    # 'X-ray' is folded first so its own hyphen is not read as a separator.
    t = re.sub(r"\bx-ray\b", "xray", text, flags=re.I)
    runs = ["".join(_NATO[w.lower()] for w in re.findall(r"[A-Za-z]+", m) if w.lower() in _NATO)
            for m in _NATO_RUN.findall(t)]
    return " ".join(r for r in runs if r)


def tag_decode(text: str) -> list:
    """Unicode TAG (U+E0000 offset) and variation-selector-supplement (U+E0100 offset) smuggling: each
    plane-14 code point carries one character (ASCII by spec; the encoder applied to Hangul simply
    lands higher in plane 14). strip_format_chars()/strip_combining() DELETE these — which hid the
    payload entirely — so decode them here. Both offsets are tried as two views (a code point above
    U+E0100 is ambiguous between them). Returns [] when fewer than 3 plane-14 chars are present."""
    if not text or sum(1 for ch in text if 0xE0000 <= ord(ch) <= 0xEFFFF) < 3:
        return []
    views = []
    for base in (0xE0000, 0xE0100):
        out = []
        for ch in text:
            o = ord(ch)
            if 0xE0000 <= o <= 0xEFFFF and o - base >= 0x20:
                out.append(chr(o - base))
            elif not (0xE0000 <= o <= 0xEFFFF):
                out.append(ch)
        views.append("".join(out))
    return views


_SB_ZERO, _SB_ONE, _SB_SPACE = "⁢", "⁤", "​"


def _sneaky_word(bits: str):
    """Parse one word of variable-length bin() codes (no leading zeros, so every code starts with '1')
    into printable ASCII 6-bit (0x20-0x3F) / 7-bit (0x40-0x7E) chars, or Hangul (16-bit syllables /
    14-bit compatibility jamo — this deployment's two locales are ko/en); prefer more letters, a
    Hangul code point weighted for its width. Bounded DP (len cap x 4 widths). Other scripts' wide
    code points are not parsed — named residual (DESIGN.md §5)."""
    n = len(bits)
    if n > 16 * 48:
        return None
    best = [None] * (n + 1)
    best[0] = (0, "")
    for i in range(n):
        if best[i] is None or bits[i] != "1":
            continue
        for w in (7, 6, 14, 16):
            j = i + w
            if j > n:
                continue
            c = int(bits[i:j], 2)
            hangul = 0xAC00 <= c <= 0xD7A3 or 0x3131 <= c <= 0x318E   # 16-bit syllables, 14-bit jamo
            if not (32 <= c <= 126 or hangul):
                continue
            score = best[i][0] + (2 if hangul else 1 if chr(c).isalpha() else 0)
            if best[j] is None or score > best[j][0]:
                best[j] = (score, best[i][1] + chr(c))
    return best[n][1] if best[n] else None


def sneaky_bits_decode(text: str) -> str:
    """'Sneaky bits' smuggling: U+2062 = 0, U+2064 = 1, U+200B = space (invisible operators, which
    strip_format_chars() deletes). Returns '' when the text holds fewer than 12 such bits."""
    if not text or text.count(_SB_ZERO) + text.count(_SB_ONE) < 12:
        return ""
    bits = "".join("0" if c == _SB_ZERO else "1" if c == _SB_ONE else " " if c == _SB_SPACE else "|"
                   for c in text if c in (_SB_ZERO, _SB_ONE, _SB_SPACE) or c.isspace())
    words = []
    for w in re.split(r"[ |]+", bits):
        if w:
            d = _sneaky_word(w)
            if d:
                words.append(d)
    return " ".join(words)


# --- R11b: Ecoji / Base2048 (alphabets generated into core/codec_tables.py by build_codec_tables.py) ---
from codec_tables import ECOJI, ECOJI_PAD, ECOJI_PAD4, B2048, B2048_TAIL  # noqa: E402

_ECOJI_IDX = {c: i for i, c in enumerate(ECOJI)}
_ECOJI_ALL = set(ECOJI) | {ECOJI_PAD} | set(ECOJI_PAD4)
_B2048_IDX = {c: i for i, c in enumerate(B2048)}
_B2048_TAIL_IDX = {c: i for i, c in enumerate(B2048_TAIL)}
_B2048_ALL = set(B2048) | set(B2048_TAIL)


def _ecoji_bytes(s: str):
    """Ecoji v1: 4 emoji -> 5 bytes (10 bits each); '☕' pads, the four PAD4 emoji carry 2 bits in the
    last slot. Newlines / VS16 inside the run are skipped. None on a malformed group."""
    cs = [c for c in s if c in _ECOJI_ALL]
    if not cs:
        return None
    out = bytearray()
    for g in range(0, len(cs), 4):
        grp = (cs[g:g + 4] + [ECOJI_PAD] * 4)[:4]
        if grp[0] not in _ECOJI_IDX:
            return None
        b = [_ECOJI_IDX.get(c, 0) for c in grp[:3]]
        c3 = grp[3]
        b3 = (ECOJI_PAD4.index(c3) << 8) if c3 in ECOJI_PAD4 else _ECOJI_IDX.get(c3, 0)
        five = [b[0] >> 2, ((b[0] & 3) << 6) | (b[1] >> 4), ((b[1] & 15) << 4) | (b[2] >> 6),
                ((b[2] & 63) << 2) | (b3 >> 8), b3 & 255]
        keep = 1 if grp[1] == ECOJI_PAD else 2 if grp[2] == ECOJI_PAD else 3 if c3 == ECOJI_PAD \
            else 4 if c3 in ECOJI_PAD4 else 5
        out += bytes(five[:keep])
    return bytes(out)


def _b2048_bytes(s: str):
    """Base2048 (qntm): 11 bits per char; the final char is either a full char carrying 4-11 bits or one
    of 8 tail chars carrying 1-3 bits, right-aligned — the bit count follows from the total length."""
    if not s or any(c not in _B2048_IDX for c in s[:-1]) or s[-1] not in _B2048_ALL:
        return None
    base = 11 * (len(s) - 1)
    if s[-1] in _B2048_TAIL_IDX:
        k = next((k for k in (1, 2, 3) if (base + k) % 8 == 0), None)
        v = _B2048_TAIL_IDX[s[-1]]
    else:
        k = next((k for k in range(4, 12) if (base + k) % 8 == 0), None)
        v = _B2048_IDX[s[-1]]
    if k is None or v >> k:
        return None
    acc = 0
    for c in s[:-1]:
        acc = (acc << 11) | _B2048_IDX[c]
    acc = (acc << k) | v
    return acc.to_bytes((base + k) // 8, "big")


def _runs(text: str, alphabet: set, skip: str, min_len: int, cap: int = 2048):
    """Maximal runs of alphabet chars; chars in `skip` (whitespace, VS16) may occur INSIDE a run and are
    dropped — codex R11b-r1: a payload split into space-separated groups slipped."""
    runs, cur = [], []
    for ch in text[:_MAX_BLOB_IN]:
        if ch in alphabet:
            cur.append(ch)
        elif ch in skip and cur:
            continue
        else:
            if len(cur) >= min_len:
                runs.append("".join(cur[:cap]))
            cur = []
    if len(cur) >= min_len:
        runs.append("".join(cur[:cap]))
    return runs[:16]


def _bits_to_text(bits: str):
    s = _printable_only(bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits) - 7, 8)).decode("utf-8", "ignore"))
    return s if len(s) >= 3 else None


def _ecoji_loose(run: str):
    """Ecoji as a raw 10-bit stream (stop at the first padding emoji) — tolerant of alphabet-valid junk
    AFTER the payload; the caller supplies the start offset (junk BEFORE it)."""
    bits = []
    for c in run:
        if c in _ECOJI_IDX:
            bits.append(format(_ECOJI_IDX[c], "010b"))
        elif c in ECOJI_PAD4:
            bits.append(format(ECOJI_PAD4.index(c), "02b"))
            break
        else:
            break
    return _bits_to_text("".join(bits))


def _b2048_loose(run: str):
    """Base2048 as a raw 11-bit stream (tail char = 3 bits, then stop)."""
    bits = []
    for c in run:
        if c in _B2048_IDX:
            bits.append(format(_B2048_IDX[c], "011b"))
        else:
            bits.append(format(_B2048_TAIL_IDX[c], "03b"))
            break
    return _bits_to_text("".join(bits))


_EMOJI_MAX_START = 24      # alphabet-valid wrapper chars glued before a payload (codex R11b-r1)
_EMOJI_WIN = 192           # a crisis / absolution payload is short


def emoji_codec_decode(text: str) -> list:
    """Ecoji / Base2048 runs -> decoded text. Whole-run strict decode first; then a bounded start-offset
    scan with a loose bit-stream decode, so alphabet-valid junk before/after the payload (an emoji, an
    Armenian word) does not shift it out of alignment. Printable filter as in _b64_try: a benign emoji
    string / Cyrillic word decodes to noise and is dropped. Bounded: 16 runs x 24 starts x 192 chars."""
    if not text:
        return []
    out = []

    def _add(s):
        if s and len(s) >= 3 and _printable_ratio(s) >= 0.85 and s not in out:
            out.append(s)

    for run in _runs(text, _ECOJI_ALL, " \t\n\r\ufe0f", 4):
        raw = _ecoji_bytes(run)
        if raw:
            _add(raw.decode("utf-8", "ignore"))
        for st in range(min(_EMOJI_MAX_START, len(run) - 3)):
            _add(_ecoji_loose(run[st:st + _EMOJI_WIN]))
    for run in _runs(text, _B2048_ALL, " \t\n\r", 3):
        raw = _b2048_bytes(run)
        if raw:
            try:
                _add(raw.decode("utf-8", "strict"))
            except UnicodeDecodeError:
                pass
        for st in range(min(_EMOJI_MAX_START, len(run) - 2)):
            _add(_b2048_loose(run[st:st + _EMOJI_WIN]))
    return out


def cipher_views(text: str) -> list:
    """R11 view family: fixed ciphers (Caesar x24, Atbash, reversal) + symbol transcodings (Morse,
    Braille, NATO, Unicode-tag/variant-selector, sneaky-bits). Byte codecs (Base32/Ascii85/Base85/
    uuencode) live in decode_blobs() so they share its bounded recursive frontier."""
    text = text or ""
    views = list(caesar_views(text))
    for v in (atbash(text), reversed_view(text), morse_decode(text), braille_decode(text),
              nato_decode(text), *tag_decode(text), sneaky_bits_decode(text)):
        if v and v != text:
            views.append(v)
    return views


# Base32 (RFC 4648, upper or lower) / Ascii85 / Base85 / uuencode — byte codecs, strict-decoded and
# printable-filtered exactly like _b64_try/_hex_try (a benign token that decodes to binary is dropped).
_B32_RE = re.compile(r"[A-Za-z2-7]{8,}={0,6}")
_A85_RE = re.compile(r"(?:<~)?[!-uz]{10,}(?:~>)?")         # Adobe Ascii85 alphabet (no whitespace)
_B85_RE = re.compile(r"[0-9A-Za-z!#$%&()*+\-;<=>?@^_`{|}~]{10,}")  # RFC 1924 / git base85 alphabet


def _b32_try(frag):
    f = frag.rstrip("=")
    if len(f) < 8:
        return None
    f = f.upper()
    try:
        s = base64.b32decode(f + "=" * (-len(f) % 8)).decode("utf-8", "strict")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None
    return s if len(s) >= 3 and _printable_ratio(s) >= 0.85 else None


def _a85_try(frag):
    f = frag
    if f.startswith("<~"):
        f = f[2:]
    if f.endswith("~>"):
        f = f[:-2]
    for dec in (lambda x: base64.a85decode(x), lambda x: base64.b85decode(x)):
        try:
            s = dec(f.encode("ascii")).decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError, TypeError):
            continue
        if len(s) >= 4 and _printable_ratio(s) >= 0.9:
            return s
    return None


def _uu_decode_lines(text: str):
    """uuencode: each line is <len-char><data>. Decode every line (or its tail after a space, so a
    'What does this mean? M...' prefix on the first line is tolerated), CONCATENATE the raw bytes of
    consecutive hits, then UTF-8-decode once — standard 45-byte lines split multi-byte (Hangul) chars
    across lines, so per-line decoding dropped them (Codex R11-r1)."""
    chunks = []
    for line in text.splitlines()[:64]:
        line = line.rstrip("\r")
        if not line or len(line) > 128:
            continue
        starts = [0] + [i + 1 for i, c in enumerate(line[:96]) if c == " "]
        for st in starts:
            seg = line[st:]
            if not seg or not (" " < seg[0] <= "M") or any(c > "`" for c in seg):
                continue
            try:
                raw = binascii.a2b_uu(seg)
            except binascii.Error:
                continue
            if len(raw) >= 2:
                chunks.append(raw)
                break
    if not chunks:
        return []
    s = _printable_only(b"".join(chunks).decode("utf-8", "ignore"))
    return [s] if len(s) >= 3 and _printable_ratio(s) >= 0.9 else []


def _wrapped_blocks(text: str, alphabet_re: str) -> list:
    """Consecutive lines that consist ONLY of a codec alphabet (a line-wrapped blob), joined with the
    line breaks / indentation removed (Codex R11-r1: Base32/Ascii85/Base85 wrapped at 8-10 chars
    slipped). Codex R11-r2: blank / whitespace-only lines INSIDE a block no longer end it (up to 2 in a
    row), and since an ordinary alphabet-only header/footer line ('Introduction', 'Thanks') joined onto
    the block breaks the codec's alignment, each block is also tried with up to 2 lines trimmed from
    either end (<= 9 candidates per block). Bounded: 256 lines considered, 16 blocks x first 512 joined chars."""
    line_re = re.compile(r"^\s*(?:%s)+\s*$" % alphabet_re)
    blocks, cur, blank = [], [], 0
    for line in text.splitlines()[:256]:
        if not line.strip():
            blank += 1
            if blank > 2 and cur:
                blocks.append(cur)
                cur = []
            continue
        if line_re.match(line):
            cur.append(line.strip())
            blank = 0
        else:
            if cur:
                blocks.append(cur)
            cur, blank = [], 0
    if cur:
        blocks.append(cur)
    out = []
    for blk in blocks[:16]:
        acc, kept = 0, []
        for ln in blk:                 # cap by JOINED length (a wrapped crisis/absolution blob is short),
            if acc >= 512:             # not by line count — width-1 wrapping makes 80+ one-char lines
                break
            kept.append(ln)
            acc += len(ln)
        blk = kept
        if len(blk) < 2:
            continue
        for lo in range(min(3, len(blk) - 1)):
            for hi in range(min(3, len(blk) - lo - 1)):
                cand = "".join(blk[lo:len(blk) - hi])
                if cand not in out:
                    out.append(cand)
    return out


_R11_DEGLUE_BUDGET = 384    # loose-window decodes per CODEC per decode_more_blobs() call (a shared budget let
#   the Base32 scan over a junk prefix starve the Ascii85/Base85 scans of the same text)
_R11_DEGLUE_MAX_RUN = 320   # a glued crisis blob is short; a longer alphabet run is not de-glued (DoS)


def _b32_loose(seg):
    """Loose Base32 window: try PADDED first (a short blob's last group is partial — truncating it to a
    multiple of 8 dropped the final byte, 'myself' -> 'mysel'), then truncated."""
    seg = seg.upper()
    for cand in (seg + "=" * (-len(seg) % 8), seg[: len(seg) // 8 * 8]):
        if len(cand.rstrip("=")) < 8:
            continue
        try:
            raw = base64.b32decode(cand)
        except (binascii.Error, ValueError):
            continue
        s = _printable_only(raw.decode("utf-8", "ignore"))
        if len(s) >= 3:
            return s
    return None


def _x85_loose(seg, dec):
    """Loose Ascii85/Base85 window: whole window first (both decoders accept a partial final group),
    then truncated to whole 5-char groups."""
    for cand in (seg, seg[: len(seg) // 5 * 5]):
        if len(cand) < 10:
            continue
        try:
            raw = dec(cand.encode("ascii"))
        except (ValueError, TypeError):
            continue
        s = _printable_only(raw.decode("utf-8", "ignore"))
        if len(s) >= 3:
            return s
    return None


def _deglue(run, loose, budget):
    """R11b — the base64/hex de-glue idea for the R11 byte codecs: a run that fails to decode whole may
    carry a valid blob glued to alphabet-junk (no separator). Scan start offsets, decode a short window
    loosely (junk tail bytes ignored), keep printable. Bounded by a SHARED budget, not per run."""
    out = []
    if len(run) > _R11_DEGLUE_MAX_RUN:
        return out
    for start in range(len(run)):
        win = run[start:start + _DEGLUE_WIN]
        if budget[0] <= 0 or len(win) < 8:
            return out
        budget[0] -= 1
        d = loose(win)
        if d:
            out.append(d)
        # suffix junk corrupts the last x85 group (codex R11b-r1: 6 junk chars beat a 4-char trim). Only
        # where this window reaches the run's END and its first 20 chars decode to a printable prefix (a
        # likely aligned start — judged on the PREFIX, since junk like 'z' can make the whole-window
        # decode raise, codex R11b-r2) are earlier end positions tried, up to 24 back, inside the budget.
        probe = loose(win[:20]) if len(win) < _DEGLUE_WIN and budget[0] > 0 else None
        if probe is not None:
            budget[0] -= 1
        if probe and len(probe) >= 10:
            for trim in range(1, min(25, len(win) - 7)):
                if budget[0] <= 0:
                    return out
                budget[0] -= 1
                e = loose(win[:-trim])
                if e:
                    out.append(e)
    return out


def decode_more_blobs(text: str) -> list:
    """R11 byte codecs beyond base64/hex: Base32, Ascii85/Base85, uuencode. Whole-run strict decode per
    candidate, then (R11b) a budgeted de-glue scan on runs that failed whole. Bounded: candidate length
    cap, per-input candidate cap, and a per-codec de-glue budget."""
    if not text or len(text) > _MAX_BLOB_IN:
        return []
    out = []

    def _add(s):
        if s and s[:_MAX_DECODED] not in out:
            out.append(s[:_MAX_DECODED])

    n = 0
    budgets = {}
    loose = {_B32_RE: [_b32_loose], _A85_RE: [lambda x: _x85_loose(x, base64.a85decode)],
             _B85_RE: [lambda x: _x85_loose(x, base64.b85decode)]}
    for rx, fn, alpha in ((_B32_RE, _b32_try, r"[A-Za-z2-7=]"), (_A85_RE, _a85_try, r"[!-uz~<>]"),
                          (_B85_RE, _a85_try, r"[0-9A-Za-z!#$%&()*+\-;<=>?@^_`{|}~]")):
        for m in rx.findall(text) + _wrapped_blocks(text, alpha):
            n += 1
            if n > 64:
                break
            whole = fn(m)
            _add(whole)
            if whole is None and len(m) >= 16:          # R11b de-glue only when the whole run failed
                for lf in loose[rx]:
                    for d in _deglue(m.rstrip("=").strip("<~>"), lf, budgets.setdefault(rx, [_R11_DEGLUE_BUDGET])):
                        _add(d)
    for s in _uu_decode_lines(text):
        _add(s)
    return out


def normalized_views(text: str):
    """Cached front for _normalized_views (pure: same text -> same views). Returns fresh copies so a
    caller mutating the list/dict cannot poison the cache. R11: grounding_gate_v5 re-normalizes every
    view once per pattern set, which made the ~40-view R11 set cost ~30x without this."""
    views, flags = _normalized_views_cached(text or "")
    return list(views), dict(flags)


@functools.lru_cache(maxsize=4096)
def _normalized_views_cached(text: str):
    views, flags = _normalized_views(text)
    return tuple(views), flags


def _normalized_views(text: str):
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
    skel_full = skeleton_full(text)              # R11: full-UTS#39 confusables, match-only (not the flag)

    # BOUNDED RECURSIVE DECODE — seed the frontier with the NORMALIZED variants too, not just raw text
    # (Codex round-9): a fullwidth-percent / zero-width-split base64 needs normalize-THEN-decode
    # (fullwidth '％' → NFKC → '%' → percent-decode; zero-width-broken base64 → format-strip → clean →
    # decode). Combined with decoded_composed (decode-THEN-normalize, round-8) this closes both orders.
    # Still bounded (depth 3, per-item caps in decode_blobs) — infinite cipher regress stays out of scope.
    # R11: cipher + transcoding views. Fixed ciphers (Caesar x24 / Atbash / reversal) are match views
    # only; the symbol transcodings (tag / sneaky-bits / braille / morse / NATO) also SEED the decode
    # frontier so a base64 blob smuggled inside invisible tag characters is still decoded.
    ciphers = cipher_views(text)
    transcoded = [v for v in (*tag_decode(text), sneaky_bits_decode(text), braille_decode(text),
                              morse_decode(text), nato_decode(text)) if v]
    decoded = set()
    frontier = list(dict.fromkeys([text, folded, skel, no_marks, apos, composed, *transcoded]))
    # ^ dedupe (codex R11b-r1 DoS): for plain ASCII the six seeds are IDENTICAL and every decoder ran 6x.
    for _depth in range(3):
        nxt = []
        for s in frontier:
            if len(s) > 4096:   # perf bound (Codex round-10): a hidden SHORT crisis fits in a small
                continue        # blob; skip decoding huge seeds (a real crisis message is not 8 KB).
            cands = list(decode_blobs(s)) + decode_more_blobs(s) + emoji_codec_decode(s)  # R11/R11b
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
    for v in (text, folded, skel, no_marks, skel_no_marks, apos, composed, skel_full,
              r13, deleet_i, deleet_l, deleet_i_r13, deleet_l_r13, *ciphers,
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
