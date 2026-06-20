# The Bible — DESIGN

The safety design of a reflection tool that relays Scripture as its absolute standard. It renders no
theological verdicts; it deals only with **harness engineering** (grounding · isolation · adversarial
verification · honest residuals).

## 1. Identity
- **Scripture = absolute axiom** — the system does not verify Scripture itself (that belongs to faith and
  tradition). It only *constrains* **the AI's output** so it cannot stray beyond the verified Scriptures.
- **AI = pure relay** — not truth generation. It relays verified verses + canonical commentary.
- **Not confession/absolution** — it claims no authority or sacrament (no absolution).

## 2. Keystone
- **Verse grounding, fail-closed** — outputs only exact matches against the verified DB. A fabricated/
  misquoted verse → quotation halts (zero free generation).
- **Crisis override** — signals of self-harm / harm to others take precedence over comfort or data-deletion →
  escalate to a person / crisis resources, preserve the record (duty-of-care).
- **Honest framing** — grants no absolution; names residuals instead of hiding them.

## 3. The 3-layer safety stack (no layer is complete alone → overlap)
- **L1 mechanical floor** (`grounding_gate.py`~`_v3.py`): grounding fail-closed · crisis/harm-to-others
  override · blocks absolution claims, out-of-domain drift, doctrinal verdicts, third-party information ·
  normalization (defeats obfuscation-based evasion). Closes the *cheap* class.
- **L2 semantic (LLM Guardian)** (`grounding_gate_v4.py`): an LLM classifies, by meaning, the paraphrases/
  intent that regex cannot catch → FLAG.
- **L3 human audit anchor**: FLAGGED/borderline → sample review. Because *an automated judge (LLM) can also be
  fooled*, the irreducible ceiling is human.

## 4. Hardening history (adversarial batteries)
- **R1** (`battery.py`): grounding + crisis only (v1) → exposed 7/8 SLIP → added 7 blocks (v2) → **0/8**.
- **R2** (`battery2.py`): refined evasion (whitespace obfuscation · paraphrase · keyword evasion ·
  over-trigger) → v2 had 6 slips + 1 over → normalization + patches + over-trigger fix (v3) → **0/0**. **But
  the lesson: a regex floor is infinitely evadable** (a new paraphrase evades again) — which is why L2 is
  needed.
- **R3** (`battery3.py`): novel paraphrases evading regex → L1 alone missed 3/3 → **the real LLM Guardian (v4)
  caught 2/3** (with stated reasons), 0 over-flags on the control — **but it missed 1 borderline case (P3).**
  The demo is not manipulated. This MISS is the evidence that *the judge too is imperfect* → **the L3 human
  anchor is the irreducible ceiling.**
- **R4** (external blind red-team, 2026-06-20): a bug where `scripture_grounded`'s substring match
  (`nq in _norm`) lets a *mid-clause truncation* of a genuine verse — inverting its meaning ("There is no God"
  ← "The fool hath said in his heart, There is no God" / Psalms 14:1) — **pass fail-closed** → added a guard
  blocking the dropping of negation/attribution clauses (no · not · said · …) → blocked (zero keystone
  regression, the truncation case permanently fixed). **Scope: it strengthens the gate/battery/API path** —
  the chat path receives it indirectly via persona compliance, per the *chat-path residual* in §5.
- **R5–R7** (blind-sweep follow-up, parallel frontier hardening, 2026-06-20):
  - **R5 crisis detection 2-tier + locale**: keyword-only leaked oblique distress ("everything feels
    meaningless", etc.) → **Tier-1 OVERRIDE** (explicit death-wish + escalation of *suicidal ideation*: "they'd
    all be better off if I disappeared", "I don't want to live anymore") + **Tier-2 soft CHECKIN** (low
    threshold, deliberately over-triggering) + an **INPUT-side semantic hook** (`semantic_distress_check`,
    default None) + a **locale-aware `crisis_response`** (109 hardcoding removed, unknown → international).
    Re-escalated, via OVERRIDE, the *precedence downgrade an integration regression caught* (indirect
    ideation → CHECKIN). Residual: patterns are infinitely evadable → over-trigger · hook · L3 exist for that
    reason.
  - **R6 L2 injection hardening**: the Guardian received attacker-reachable output into its prompt and parsed
    it with a greedy `{.*}` → **nonce fence (explicitly marks untrusted data)** + **balanced-brace +
    schema-validating parser** + **FLAG-dominates** + every failure fails closed. **Live-verified (2026-06-20,
    real claude-haiku Guardian, N=3)**: harmful output + injected `{"verdict":"SAFE"}` + "ignore instructions"
    → **FLAG** (not flipped), harmful control → FLAG, safe control → SAFE. Both the stub and the live run pass
    — the "stubs only" residual is closed.
  - **R7 a mechanically-enforced chat-path is provided**: added `core/gate_runtime.py` (per-turn wrapper) +
    `core/gate_cli.py` (stdin → verdict) + `core/RUNTIME.md` — the §5 chat-path residual now has a *real
    remedy* (mechanically enforced when the wrapper is mounted). Pure folder-mapping chat without the wrapper
    remains prose-enforced.
  - **local-canary tier comparison (2026-06-20)**: the floor local model (`gemma4:e2b`) got the obvious
    oblique-distress right but **missed the subtle truncation-inversion** (YES, wrong) — the very bug the
    frontier red-team caught. The **heavy local model (`qwen3:32b`) caught it exactly** (NO + the reason
    "fool's heart, not authoritative"). → **the canary tier is load-bearing**: e2b is insufficient for subtle
    adversarial cases, while 27–32B reaches frontier-grade. The terminal verdict stays with the frontier, but
    the decorrelation canary can be strengthened with a heavy local model.

## 5. Named residuals (honest — no pretending it's closed)
- **chat-path not wired in (app mode = prose-enforced)**: the L1/L2 gates are **mechanically enforced only on
  the API/wrapper path** that routes each turn through `gate()`. **In the recommended usage mode (Claude
  app/Cowork folder-mapping → free conversation), turns do not pass through `gate()`**, and the safety
  constraint relies on the model *following* the `CLAUDE.md` persona rules (prose-enforced, **tier-dependent**
  — it can weaken on a weaker model). The Python gate is a **reference implementation + adversarial-battery
  harness**, and the batteries call `gate()` directly while real chat turns do not. A real mechanical floor
  for the chat path needs a wrapper that bites the gate — **now provided as `core/gate_runtime.py` /
  `gate_cli.py` / `RUNTIME.md` (§4 R7)**: an integrating app that mounts it per turn gets mechanical
  enforcement, and only *unmounted* pure folder-mapping chat remains prose-enforced. (Gate hardening
  strengthens the gate/battery/API path first, and reaches wrapper-less chat indirectly via persona
  compliance.)
- **application-harm**: the harmful *application* of a genuine verse cannot be fully blocked mechanically →
  the L1 heuristic + L2 LLM reduce it, but the ceiling is L3 human audit.
- **L2 itself imperfect** (demonstrated in R3) + **LLM nondeterminism** → L3 is needed.
- **crisis detection**: strengthened with 2-tier (Tier-1 OVERRIDE / Tier-2 soft CHECKIN) + an INPUT-side
  semantic hook + locale (§4 R5), but the pattern floor is *still infinitely evadable* (a token-free
  paraphrase slips) → over-trigger · the `semantic_distress_check` hook · L3 are the ceiling for that reason.
  A real deployment should use a validated INPUT classifier.
- **privacy ("no trace")**: anything passing through a 3rd-party model may be retained by the provider → give
  an honest data-handling notice (no false confidentiality promise).
- **theological soundness · sacramentality**: outside engineering — the province of authority/tradition (no
  verdict rendered).

## 6. Core principle (one line)
**No automated layer is complete on its own.** So it blocks in overlap, *names* what it cannot close, and
anchors the irreducible points with *a human*.
