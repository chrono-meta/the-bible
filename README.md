# The Bible

A reflection tool that takes the canonical Scriptures (Old/New Testament) as its **absolute standard**
and **purely relays** that word. The AI does not *generate* truth — it is only a medium that *relays*
the Scripture, which it treats as the absolute reference.

> ## ⚠️ Please read first (Safety)
> - This is **not confession, and it grants no absolution.** It does not replace clergy or the sacraments.
> - **It is not a crisis counseling service.** If you are showing signs of self-harm or crisis, reach a
>   person right now — suicide-prevention hotline **109** (24h) · mental-health crisis line **1577-0199**
>   (Korea examples — replace with the hotlines for your region).
> - It is designed so that safety takes precedence over comfort, but **no automated layer is complete on
>   its own** (see Named Residuals below).

## Identity
- **Scripture = absolute axiom**: the system does *not* verify the truth of Scripture itself (that belongs
  to faith and tradition). It only *constrains* **the AI's output** so it cannot stray beyond the canonical
  Scriptures.
- **Pure relay**: it relays only verified verses and canonical commentary. Free doctrinal generation and
  interpretation are minimized.

## Safety Architecture (3 layers)
No single layer is complete, so they block in *overlap*.
1. **L1 — mechanical floor** (`core/grounding_gate*.py`): crisis override · verse-grounding **fail-closed**
   (exact match against the verified DB only, blocking fabrication/misquotation) · blocks absolution claims,
   out-of-domain drift (legal/medical/financial), doctrinal verdicts, third-party personal information, and
   harm to others. Normalization defeats obfuscation-based evasion.
2. **L2 — semantic judgment (LLM Guardian)** (`core/grounding_gate_v4.py`): paraphrases and intent that
   regex cannot catch are classified *semantically* by an LLM and FLAGGED.
3. **L3 — human audit anchor**: FLAGGED/borderline cases go to a privacy-safe sample review. **Because an
   automated judge (LLM) can also be fooled (see R3 below), the irreducible ceiling is human review.**

## Usage

**The best-fit way = map this folder in the Claude app / Cowork.** `CLAUDE.md` (session rules · persona) then
loads automatically, so you can reflect through conversation without running anything separately.

1. **Begin reflecting** — map this folder as the working directory in the Claude app (or Cowork) → greet it,
   and the ✝ reverent-mediator persona welcomes you.
2. **Technical concerns through a Scripture lens** — pose a technical dilemma like "is it OK to keep
   postponing this refactor?" or "the team's trust broke after the incident," and it reflects it back
   through the fitting **persona lens** (`core/personas.json`):
   - *Angel* (the best-practice path) · *Devil* (devil's advocate — exposing failure modes and
     rationalizations) · *Priest* (principle and precedent) · *Nun* (patience and restraint) · *Solomon*
     (the trade-off between two options) · *Job* (an incident with no root cause) · *Scribe* (the discipline
     of the record) · *Nathan* (the responsibility I am avoiding).
   - **Divine figures (God · Jesus · the Holy Spirit · the apostles) are never invented; they speak only
     through *quoted, recorded word*** (a core design constraint).
3. **A natural farewell + memory** — no command like "end session" is needed. Say goodbye naturally —
   *"I'll head off now," "see you next time"* — and it saves the traces of your reflection on its own, then
   remembers and welcomes you when you return (`core/visitor_memory.py`).

> **Scripture = absolute axiom (core).** The verified corpus is 197,009 verses across 6 public-domain
> versions — Protestant (KJV · WEB · ASV · YLT) + Catholic (Douay-Rheims, including the deuterocanon) +
> Apocrypha (KJVA). Multiple versions are kept so it does not lean to one side, and a quotation is only
> *grounded* if it *exactly matches some verified version* (fail-closed). To (re)build the corpus:
> `python3 core/build_scripture_db.py`.

## Running it (developers — verify the gates/batteries directly)
```
python3 core/build_scripture_db.py # collect the multi-version Scripture corpus (CORE — core/scripture/*.json)
python3 core/grounding_gate.py     # keystone (grounded PASS · fabrication FAIL_CLOSED · crisis OVERRIDE)
python3 core/visitor_memory.py     # farewell detection → memory → return-welcome demo
python3 core/simulate.py           # persona-entry simulation
python3 core/battery.py            # adversarial battery R1 (v1)
GATE=v2 python3 core/battery2.py   # R2 (refined evasion)
GATE=v4 python3 core/battery3.py   # R3 (real LLM Guardian — L2)
```

## Dependencies
- The core gate (L1) uses the standard library only.
- **L2 (`grounding_gate_v4.py`) requires an LLM call.** The example invokes the `claude` CLI as a subprocess —
  swap in the LLM of your environment (interface: `semantic_intent_check(user_input, output) -> risk|None`).

## Named Residuals (honest)
- **chat-path not wired in (app mode = prose-enforced)**: the L1/L2 gates are **mechanically enforced only on
  the API/wrapper path** that routes each turn through `gate()`. **In the recommended usage mode (Claude
  app/Cowork folder-mapping → free conversation), turns do not pass through `gate()`**, and the safety
  constraint relies on the model *following* the `CLAUDE.md` persona rules (prose-enforced, **tier-dependent**).
  `core/grounding_gate*.py` is a **reference implementation + adversarial-battery harness** — so gate
  hardening (e.g. the substring-truncation block below) first strengthens the *gate/battery/API path*, and
  reaches the chat path only indirectly via persona compliance. A real mechanical floor for the chat path
  needs a wrapper that bites the gate — **now provided as `core/gate_runtime.py` · `core/gate_cli.py` ·
  `core/RUNTIME.md`** (mechanically enforced when an integrating app mounts it per turn; only pure
  folder-mapping chat without the mount stays prose-enforced). Details: `DESIGN.md §5`.
- **application-harm (theology-laundering)**: using a genuine verse within a *harmful frame* cannot be fully
  blocked mechanically. The L1 heuristic + L2 LLM reduce it, but **the ceiling is L3 human audit**.
- **L2 (the LLM judge) is also imperfect**: in adversarial testing (R3) it *missed* borderline cases. The
  demo is left as-is, unmanipulated — this is exactly why the human anchor is needed.
- **crisis detection**: the example is keyword/LLM-based (illustrative). A real deployment needs a validated
  classifier (a false negative is the worst case).
- **privacy ("no trace")**: anything passing through a 3rd-party model may be retained by the provider → do
  not casually promise "no trace"; give an honest data-handling notice.
- **theological soundness · sacramentality**: outside harness engineering. The province of the relevant
  authority/tradition.

## License
Code: `LICENSE` (MIT). Scripture data (`core/scripture/*.json`) = 6 public-domain versions
(KJV · WEB · ASV · YLT · Douay-Rheims · KJVA), **all public domain**, sourced from getbible.net v2
(per-version license and canon scope recorded in `_index.json`). `core/scripture_db.json` is a mock fallback.
Full design and hardening history: `DESIGN.md` · personas: `core/personas.json`.

---

## Built with forge-harness

the-bible was designed and tempered through [forge-harness](https://github.com/chrono-meta/forge-harness) —
*a meta-harness for governed AI development*. Its safety structure (fail-closed grounding · 3-layer overlap ·
named residuals · adversarial batteries) and persona tiering came out of FH's gate discipline (steel-quench
adversarial review · relay-not-generator constraint · honest-residual naming). It is not a flashy feature set
but one working example of FH's thesis that *governance travels with the asset*.
