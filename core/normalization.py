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
  - leetspeak (3→e, 1→l) is deliberately NOT folded: digit→letter folding over-triggers on ordinary
    text ("Psalm 23"). It is left to the optional CPT hook / L2, named here.
  - Caesar/reversed/rot13 ciphers are not decoded by the stdlib floor (unbounded) — the CPT hook / L2
    are the path for those. base64/hex are decoded because they are bounded and lossless.
"""
import base64
import binascii
import re
import unicodedata

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
_B64_RE = re.compile(r"[A-Za-z0-9+/]{12,}={0,2}")
_HEX_RE = re.compile(r"(?:[0-9a-fA-F]{2}\s*){8,}")
_MAX_BLOB_IN = 8192    # ignore absurdly long candidate blobs (DoS guard, F5)
_MAX_DECODED = 4096    # cap decoded view length fed to the pattern rescan
_MAX_BLOBS = 8         # cap how many blobs we decode per input


def _printable_ratio(s: str) -> float:
    if not s:
        return 0.0
    printable = sum(1 for c in s if c.isprintable() or c in (" ", "\n", "\t"))
    return printable / len(s)


def decode_blobs(text: str) -> list:
    """Find base64/hex blobs, decode, return decoded strings that are mostly printable text (so an
    intent encoded to dodge the patterns gets re-scanned in the clear).

    Bounded + lossless: only well-formed blobs that strict-decode to readable text are returned; a
    random token that is base64-shaped but decodes to binary is dropped. Length/count capped (F5).
    NOTE: a benign token decoding to clean text (e.g. an API key → 'SomeVerifyToken123') IS returned
    here as a rescan view, but it does NOT by itself raise the obfuscation FLAG (see normalized_views,
    F4) — only a SAFETY-PATTERN hit on the decoded view blocks.
    """
    if not text:
        return []
    decoded = []
    for m in _B64_RE.findall(text):
        if len(decoded) >= _MAX_BLOBS:
            break
        if len(m) > _MAX_BLOB_IN:
            continue
        try:
            raw = base64.b64decode(m + "=" * (-len(m) % 4), validate=True)
            s = raw.decode("utf-8", errors="strict")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
        if len(s) >= 3 and _printable_ratio(s) >= 0.85:
            decoded.append(s[:_MAX_DECODED])
    for m in _HEX_RE.findall(text):
        if len(decoded) >= _MAX_BLOBS:
            break
        hx = re.sub(r"\s+", "", m)
        if len(hx) % 2 or len(hx) > _MAX_BLOB_IN:
            continue
        try:
            s = bytes.fromhex(hx).decode("utf-8", errors="strict")
        except (ValueError, UnicodeDecodeError):
            continue
        if len(s) >= 3 and _printable_ratio(s) >= 0.85:
            decoded.append(s[:_MAX_DECODED])
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
    blobs = decode_blobs(text)

    views = []
    seen = set()
    for v in (text, folded, skel, no_marks, skel_no_marks, *blobs):
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
        "decoded_blob": bool(blobs),
        "cpt": cpt,
    }
    # FLAG trigger (obfuscation detected but de-obfuscated clean -> L3). decoded_blob is DELIBERATELY
    # NOT a trigger (F4): a benign base64 token decoding to clean text must not FLAG — only a
    # safety-pattern hit on the decoded VIEW blocks (the caller re-matches views). The flag fires on
    # homoglyph / suspicious zero-width-bidi / a positive CPT-hook verdict.
    flags["obfuscation_attempted"] = bool(homoglyph or suspicious_format or cpt is True)
    return views, flags
