#!/usr/bin/env python3
"""
The Bible — dialogue-mode composed gate.

Composes the UNCHANGED grounding_gate_v3.gate() with dialogue_grounding_extra.extra_check()
(Unsafe-Dominant Merge, DESIGN.md §4 — the most-unsafe verdict wins, same principle the repo
already uses to merge multiple parsed verdict objects from one L2 response). This is the entry
point core/RUNTIME.md's Option 2 protocol should call for the character-dialogue/cathedral mode
(CLAUDE.md §Character Dialogue & Cathedral) instead of calling gate_cli.py/grounding_gate_v3
directly — everywhere else in this repo (the lens mode, plain relay) is unaffected and keeps
using the base gate unchanged.

Verdict precedence: base gate first (it already has crisis-override/absolution/adjudication
precedence baked in — see grounding_gate_v3.gate's own ordering). Only when the base gate PASSes
does the extra check get a say — same "floor wins first" principle gate_runtime.py's L2 hook
already uses. If the extra check fires, its UNGROUNDED_ATTRIBUTION verdict is blocking (same as
every other non-PASS verdict) and its "blocked" field is True.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grounding_gate_v3 import gate as _gate_v3  # noqa: E402
from dialogue_grounding_extra import extra_check  # noqa: E402


def dialogue_gate(user_input: str, candidate_output: str, citations=None, locale=None) -> dict:
    citations = citations or []
    result = dict(_gate_v3(user_input, candidate_output, citations, locale=locale))
    result.setdefault("verdict", "PASS")
    result.setdefault("output", candidate_output)

    if result["verdict"] == "PASS":
        extra = extra_check(user_input, candidate_output, citations, locale=locale)
        if extra is not None:
            result = extra

    result["blocked"] = result["verdict"] != "PASS"
    return result


def _demo():
    print("=== dialogue_gate — composed check demo ===\n")
    cases = [
        ("grounded persona quote", "요즘 지칩니다",
         "오라 — \"Come unto me, all ye that labour and are heavy laden, and I will give you "
         "rest.\" (Matthew 11:28)",
         [("Come unto me, all ye that labour and are heavy laden, and I will give you rest.",
           "Matthew 11:28")]),
        ("uncited authority formula (Finding 1, now caught)", "요즘 지칩니다",
         "내가 진실로 진실로 너희에게 이르노니, 너의 짐은 이미 내려놓아졌다.", []),
        ("Korean ref, uncited (Finding 2, now caught)", "요즘 지칩니다",
         "평안하라 (마태복음 11:28)", []),
        ("absolution attempt (base gate, unaffected)", "제가 잘못했어요",
         "당신은 용서받았습니다.", []),
    ]
    for label, ui, out, cites in cases:
        r = dialogue_gate(ui, out, cites)
        print(f"[{label}]")
        print(f"  verdict: {r['verdict']}  blocked={r['blocked']}")
        print(f"  output : {r['output'].splitlines()[0]}")
        print()


if __name__ == "__main__":
    _demo()
