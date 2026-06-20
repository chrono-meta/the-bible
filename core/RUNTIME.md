# Mechanical Gate Enforcement at Runtime

The safety gate (`core/grounding_gate*.py`'s `gate(user_input, candidate_output,
citations)`) is the mechanical floor of this tool: it fails closed on unverified or
meaning-inverting scripture, and overrides everything on a crisis signal. Until now it was
exercised only by the battery tests — **the recommended usage (Claude app folder-mapping →
free chat) does not route live turns through `gate()`**, so in that mode safety is
*prose-enforced* (the model is asked to behave by guidance), not *mechanically* enforced.

This directory now ships a thin runtime layer so an integrating app/agent CAN enforce the
gate per turn:

| File | Role |
|---|---|
| `gate_runtime.py` | In-process wrapper. `run_turn(user_input, candidate_output, citations)` runs the gate once per turn and returns the verdict. Import this from a Python chat agent. |
| `gate_cli.py` | stdin→stdout JSON bridge over `run_turn`. Stdlib only. Makes the gate callable as an external tool by ANY runtime (subprocess, shell pipe, MCP wrapper). |

Neither file reimplements the gate — both import the existing `gate()` engines
(`grounding_gate.py` for L1; `grounding_gate_v3.py` for L1+L2-hook).

---

## (a) How to wire mechanical enforcement into a deployment

Three options, pick by how your agent runtime is shaped.

### Option 1 — In-process (Python agent)

Call `run_turn` once for every candidate reply, **before** showing it to the user:

```python
from core.gate_runtime import run_turn

result = run_turn(user_input, candidate_reply, citations)   # citations = [(quote, ref), ...]
if result["blocked"]:                  # verdict != PASS
    reply_to_user = result["output"]   # the gate's safe substitution (crisis line / fail-closed notice)
else:
    reply_to_user = candidate_reply    # PASS — surface unchanged
```

- `verdict` is one of `PASS` / `CRISIS_OVERRIDE` / `FAIL_CLOSED` / `REFUSED` / `REDIRECTED`
  / `FLAGGED`. Only `PASS` lets the candidate through unchanged; everything else means
  surface `result["output"]` instead.
- `engine="auto"` (default) uses `grounding_gate_v3` if importable (adds REFUSED /
  REDIRECTED / FLAGGED + an L2 hook), else falls back to L1 (`grounding_gate`).
  Pin `engine="l1"` for the stdlib-only floor only.
- **Optional L2 semantic hook:** pass `l2=callable`. It is consulted only when the L1 floor
  already returned PASS (the safety floor wins first). A truthy return downgrades the turn
  to `FLAGGED`. A real deployment plugs an LLM-Guardian here — its verdict is *judged*, so
  it must be anchored by L3 human audit (an LLM judging an LLM is self-referential). The
  hook is off by default and never required for the L1 floor.

### Option 2 — External tool / subprocess (any runtime)

Pipe each candidate turn as JSON through `gate_cli.py`:

```bash
echo '{"user_input":"...","candidate_output":"...","citations":[["<quote>","<ref>"]]}' \
  | python3 core/gate_cli.py
```

Output is one verdict JSON object. **Exit codes:** `0` = PASS (surface unchanged), `1` =
blocked (surface the returned `output`), `2` = input error. Stdlib only — no install needed.

### Option 3 — MCP (optional)

`gate_cli.py` ends with a clearly-marked, commented-out FastMCP stub (`gate_turn` tool).
It **requires the `mcp` package** (`pip install mcp`) and is not part of the stdlib path —
uncomment it to expose the gate as an MCP tool over stdio. The stdlib CLI (Option 2) is the
primary, always-works bridge.

---

## (b) The honest residual

**Pure folder-mapping chat WITHOUT this wrapper stays prose-enforced** — the gate code is
never invoked, so grounding/crisis safety depends on the model following CLAUDE guidance.
That is **tier-dependent**: a strong model honors the prose floor more reliably than a weak
one, and neither is the mechanical guarantee that `run_turn` / `gate_cli.py` provides. To
get the mechanical floor you must route each turn through this layer (Option 1, 2, or 3).

Residuals that remain even *with* the wrapper (inherited from the gate, named — not hidden):

- **L1 is a mechanical floor, not a semantic solve.** It closes fabricated scripture,
  the demonstrated polarity-inversion truncation class, and crisis-keyword overrides.
  The *harmful-framing* class (a whole, true verse used harmfully) and trailing-clause
  drops are FLAGGED at best and routed to L2/L3 — see `grounding_gate_v3.py` and DESIGN §5.
- **L2 is judged, so it is anchored by L3.** Any LLM-Guardian verdict is self-referential
  (an LLM judging an LLM); the irreducible ceiling is human audit. The wrapper surfaces L2
  as `FLAGGED`, it does not treat L2 as a terminal pass.
- **Citations must be supplied by the integrator.** The gate verifies the `(quote, ref)`
  pairs it is given; if an integration does not extract citations from a reply, ungrounded
  scripture in that reply is not checked. Extraction is the integrator's job.

---

## (c) 3-line quickstart

```bash
python3 core/gate_runtime.py                                                   # see all 4 verdicts via the wrapper demo
echo '{"user_input":"x","candidate_output":"God helps those who help themselves.","citations":[["God helps those who help themselves.","Proverbs 14:23"]]}' | python3 core/gate_cli.py   # -> FAIL_CLOSED, exit 1
# In your agent: result = run_turn(user_input, candidate_reply, citations); show result["output"] when result["blocked"].
```
