#!/usr/bin/env python3
"""
The Bible — gate_runtime: a thin PER-TURN enforcement wrapper.

WHY THIS FILE EXISTS
--------------------
The grounding gate (core/grounding_gate*.py's `gate(user_input, candidate_output,
citations)`) is the mechanical safety floor of this tool. But the *recommended* usage
(Claude app folder-mapping → free chat) does NOT route conversation turns through
`gate()` — so in that mode safety is PROSE-enforced only (the model is asked, in CLAUDE
guidance, to behave). That residual is named honestly in the docs.

This wrapper closes the gap for any integration that CAN call code per turn: an
integrating chat agent calls `run_turn(...)` once for each candidate reply BEFORE it is
shown to the user. If the verdict is not PASS, the wrapper's safe `output` is what should
be surfaced instead — the gate has already substituted the safe text.

It does NOT reimplement the gate. It imports the existing `gate()` functions and adds:
  - a single call site (`run_turn`) intended to be the per-turn enforcement point,
  - an optional L2 semantic hook (off by default; opt-in via `l2=...`),
  - a stable return contract (always a dict with at least "verdict" + "output").

LAYERS
------
  L1 (default)  — grounding_gate.gate  (stdlib only): CRISIS_OVERRIDE / FAIL_CLOSED / PASS.
  L1+ (engine=v3) — grounding_gate_v3.gate (stdlib only): adds REFUSED / REDIRECTED /
                  FLAGGED and an L2 semantic-intent HOOK (stub in-repo).
  L2 (optional) — a caller-supplied callable `l2(user_input, candidate_output) -> dict|None`.
                  Only consulted when the L1/L1+ verdict is PASS (safety floor wins first).
                  A real deployment plugs an LLM-Guardian here; its JUDGED verdict must be
                  anchored by L3 human audit (an LLM judging an LLM is self-referential —
                  see grounding_gate_v3 docstring). Off by default; never required for L1.

L2 is INTENTIONALLY not wired to any model here: the primary wrapper stays stdlib-only and
deterministic. The `--l2` demo path shows the contract, not a model call.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the existing gate engines — do NOT reimplement them.
from grounding_gate import gate as _gate_l1, _has_korean  # noqa: E402

try:
    from grounding_gate_v3 import gate as _gate_v3  # noqa: E402
    _HAVE_V3 = True
except Exception as _e:  # pragma: no cover - v3 depends on v2; degrade gracefully to L1.
    _gate_v3 = None
    _HAVE_V3 = False
    _V3_IMPORT_ERR = repr(_e)

# Verdicts the integrator MUST treat as "do not surface the candidate as-is".
# (PASS is the only verdict that lets candidate_output through unchanged.)
BLOCKING_VERDICTS = frozenset(
    {"CRISIS_OVERRIDE", "FAIL_CLOSED", "REFUSED", "REDIRECTED", "FLAGGED"}
)


def _select_engine(engine: str):
    """Return (gate_fn, engine_name). 'auto' prefers v3 if importable, else L1."""
    engine = (engine or "auto").lower()
    if engine in ("l1", "v1", "base"):
        return _gate_l1, "l1"
    if engine in ("v3", "l1plus", "full"):
        if not _HAVE_V3:
            raise RuntimeError(
                "grounding_gate_v3 unavailable: %s" % globals().get("_V3_IMPORT_ERR", "?")
            )
        return _gate_v3, "v3"
    # auto
    if _HAVE_V3:
        return _gate_v3, "v3"
    return _gate_l1, "l1"


def run_turn(user_input, candidate_output, citations=None, *, engine="auto", l2=None):
    """Run ONE conversation turn through the mechanical gate. Call this per turn.

    Args:
      user_input        : the user's message for this turn.
      candidate_output  : the assistant reply the integrator is about to show.
      citations         : list of (quote, ref) pairs the candidate relies on. Each pair
                          is verified against the scripture DB; an unverified verse ->
                          FAIL_CLOSED. May be None/[] when the reply cites no scripture.
      engine            : "auto" (default; v3 if available else l1) | "l1" | "v3".
      l2                : optional callable l2(user_input, candidate_output) -> dict|None.
                          Consulted ONLY when the L1/L1+ verdict is PASS. A truthy return
                          (dict) downgrades the turn to FLAGGED with that dict's "msg"/"output".

    Returns:
      A dict that always contains "verdict" and "output", plus:
        "engine"   : which gate engine ran ("l1"/"v3"),
        "blocked"  : True unless verdict == "PASS",
        "l2"       : present only when the L2 hook produced the verdict.
      The integrator surfaces result["output"] (the gate's safe substitution when blocked,
      or the unchanged candidate when PASS).
    """
    citations = citations or []
    gate_fn, engine_name = _select_engine(engine)

    result = dict(gate_fn(user_input, candidate_output, citations))
    result.setdefault("verdict", "PASS")
    result.setdefault("output", candidate_output)
    result["engine"] = engine_name

    # Optional L2 — only when the safety floor passed (floor wins first, by design).
    if l2 is not None and result["verdict"] == "PASS":
        try:
            sem = l2(user_input, candidate_output)
        except Exception as e:  # an L2 failure must never crash the turn; fail safe-open to L1 PASS.
            sem = None
            result["l2_error"] = repr(e)
        if sem:
            result = {
                "verdict": "FLAGGED",
                "output": sem.get("msg") or sem.get("output")
                or ("의도 검토 필요 (인간 감사)." if _has_korean(user_input)
                    else "intent needs review (human audit)."),
                "engine": engine_name,
                "l2": sem,
                "note": "L2 semantic hook (JUDGED — anchor with L3 human audit)",
            }

    result["blocked"] = result["verdict"] != "PASS"
    return result


def _demo():
    print("=== gate_runtime — per-turn enforcement wrapper demo ===")
    print("(engine selected by run_turn; PASS lets candidate through, else gate substitutes)\n")
    cases = [
        (
            "평안을 구합니다",
            "Come unto me, all ye that labour and are heavy laden, and I will give you rest. (Matthew 11:28)",
            [("Come unto me, all ye that labour and are heavy laden, and I will give you rest.", "Matthew 11:28")],
            "GROUNDED quote -> expect PASS",
        ),
        (
            "위로가 필요해요",
            "God helps those who help themselves. (Proverbs 14:23)",
            [("God helps those who help themselves.", "Proverbs 14:23")],
            "FABRICATED verse -> expect FAIL_CLOSED",
        ),
        (
            "신앙이 흔들려요",
            'Scripture says: "There is no God." (Psalms 14:1)',
            [("There is no God", "Psalms 14:1")],
            "TRUNCATION (real verse sliced to invert) -> expect FAIL_CLOSED",
        ),
        (
            "더 살 이유가 없는 것 같아요",
            "(any scripture reply)",
            [],
            "CRISIS -> expect CRISIS_OVERRIDE",
        ),
    ]
    for ui, out, cites, label in cases:
        r = run_turn(ui, out, cites, engine="l1")  # pin L1 so the demo is engine-stable
        print(f"[{label}]")
        print(f"  engine : {r['engine']}")
        print(f"  verdict: {r['verdict']}  (blocked={r['blocked']})")
        print(f"  output : {r['output'].splitlines()[0]}")
        if r.get("ungrounded"):
            print(f"  ungrounded: {r['ungrounded']}")
        if r.get("actions"):
            print(f"  actions: {r['actions']}")
        print()

    # Optional L2 demo: a trivial caller-supplied hook that flags one phrase.
    def _example_l2(user_input, candidate_output):
        if "투자 확신" in candidate_output or "investment conviction" in candidate_output:
            return {"msg": ("성구를 투자 확신의 근거로 쓸 수 없습니다. (L2 → 인간 감사)"
                            if _has_korean(user_input)
                            else "Scripture cannot ground an investment conviction. (L2 → human audit)")}
        return None

    r = run_turn(
        "이 종목 괜찮을까요",
        "하나님이 함께하시니 이 투자 확신을 가지세요.",
        [],
        engine="l1",
        l2=_example_l2,
    )
    print("[L2 hook demo — caller-supplied semantic flag]")
    print(f"  verdict: {r['verdict']}  (blocked={r['blocked']})")
    print(f"  output : {r['output'].splitlines()[0]}")
    print(f"  l2     : {r.get('l2')}")


if __name__ == "__main__":
    _demo()
