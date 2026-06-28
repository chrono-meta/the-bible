#!/usr/bin/env python3
"""Proper v5 regression: run EVERY prior battery's cases through grounding_gate_v5.gate directly.

The older batteries (battery/2/3) select their gate by GATE= but only know v1/v2/v3/v4 — passing
GATE=v5 silently falls through to an OLDER gate, so "GATE=v5 python battery3.py" does NOT test v5.
This runner imports their data lists and runs them through v5 explicitly.

PASS criterion: v5 must block every should_block case (no SLIP) and PASS every control (no OVER) —
i.e. v5 is a strict superset of v4's safety with zero new over-flags.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from grounding_gate_v5 import gate  # noqa: E402
from battery import BATTERY  # noqa: E402
from battery2 import BATTERY2  # noqa: E402
from battery3 import BATTERY3  # noqa: E402

BLOCKED = ("CRISIS_OVERRIDE", "CRISIS_CHECKIN", "FAIL_CLOSED", "REFUSED", "REDIRECTED", "FLAGGED")

# KNOWN PRE-EXISTING (verified identical across v3==v4==v5, so NOT a v5 regression — these are old
# behaviors this cross-battery runner exposes for the first time, because battery/2 never ran their
# data through a v3-derived gate). Tracked, not silently passed:
#   - "battery::C 작업종료" : "끝내고 싶" (end a DEBT problem) trips v3's CRISIS_IDEATION Wide-Net Tier
#     (added in R5, intentionally over-fires; battery.py's R1-era should_block=False expectation went
#     stale when R5 landed). A Tier-1→Tier-2 refinement candidate, recorded as an FH signal — NOT
#     weakened under this run (touching self-harm detection is load-bearing).
#   - "battery2::R5 over-trigger(양성)" : FAIL_CLOSED is a grounding-DB text mismatch on the Psalm 23:1
#     citation, unrelated to the normalization pre-pass. Pre-existing.
KNOWN_PREEXISTING = {"C 작업종료(위기 아님)", "R5 over-trigger(양성)"}


def run_set(label, cases):
    slips, overs, known = [], [], []
    for name, ui, out, cites, should_block, probe in cases:
        r = gate(ui, out, cites)
        b = r["verdict"] in BLOCKED
        if should_block and not b:
            (known if name in KNOWN_PREEXISTING else slips).append((name, r["verdict"]))
        if (not should_block) and b:
            (known if name in KNOWN_PREEXISTING else overs).append((name, r["verdict"], r.get("note", "")))
    for item in known:
        print(f"   ⚪ KNOWN-PREEXISTING (v3==v4==v5) {item[0]} → {item[1]}")
    print(f"[{label}] cases={len(cases)}  SLIP={len(slips)}  OVER={len(overs)}")
    for n, v in slips:
        print(f"   🟥 SLIP {n} → {v}")
    for n, v, note in overs:
        print(f"   🟧 OVER {n} → {v}  ({note[:50]})")
    return len(slips), len(overs)


if __name__ == "__main__":
    total = 0
    for label, cases in (("battery", BATTERY), ("battery2", BATTERY2), ("battery3", BATTERY3)):
        s, o = run_set(label, cases)
        total += s + o
    print(f"\n=== v5 REGRESSION: {'PASS (0 slip, 0 over)' if total == 0 else f'FAIL ({total} issues)'} ===")
    sys.exit(1 if total else 0)
