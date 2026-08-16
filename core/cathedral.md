# The Cathedral (성당) — a second entry door

A ritual-shaped entry, distinct from both the engineering-lens mode (`core/personas.json`) and
free character dialogue (`core/personas_dialogue.json`). Two rooms:

```
성당에 들어가시겠습니까?
  ① 금언 듣기 (hear a maxim)
  ② 참회하기 (confession)
```

## ① 금언 듣기 (hear a maxim) — the safe room

This is the existing relay mechanism wearing a different door. The user names a concern (or
nothing — "아무거나 들려주세요") and receives ONE verified verse, grounded exactly as every other
relay quotation is (`scripture_grounded`, fail-closed on any mismatch). No new mechanism, no new
risk — it is included here only so the cathedral's two rooms are named as a pair.

## ② 참회하기 (confession) — the room that needed redesign

**What it is not**: a sacrament. The tool grants no absolution — this is unchanged from every
other document in this repo (`DESIGN.md §1`, `CLAUDE.md`, `README.md`). `ABSOLUTION_3` in
`grounding_gate_v3.py` already blocks the literal declaration ("I absolve you", "사함을 받았습니다",
"깨끗합니다", "무죄") mechanically, regardless of which persona is speaking — that invariant is not
touched by this design.

**What it is**: the user speaks something they regret. The response has three parts, in order,
and none of the three may be skipped:

1. **Witness, not verdict.** Name what was shared, without minimizing or amplifying it. No moral
   grade attached ("that was wrong of you" is itself an adjudication-shaped act — avoid it; so is
   "that's not so bad").
2. **A grounded verse on repentance/mercy — never a grounded verse declaring the outcome
   accomplished.** Psalm 51 ("Have mercy upon me, O God... wash me thoroughly from mine
   iniquity") is a *request* voiced by someone in the same position as the user — quoting it is
   categorically different from the tool *declaring* "you are washed." The distinction is
   grammatical: a psalm of petition, not a pronouncement of absolution. Any verse used here still
   goes through the normal citation-grounding check — this room does not relax that floor.
3. **Explicit boundary + redirect.** State plainly that this medium does not declare/pronounce
   forgiveness, then point outward — a person, a community, clergy, the sacrament if the user's
   tradition has one. This is not a caveat bolted onto a therapeutic answer; it IS the answer's
   shape.
   🟥 **Do NOT literally reuse the gate's own refusal string** ("이 매개는 죄를 사할 수 없습니다") —
   calibration (`core/simulate_dialogue.py` case ③, run 2026-08-16) found that `ABSOLUTION`'s
   `죄를\s*사` pattern has no negation-lookaround, so the negated sentence trips its own trigger and
   the compliant draft gets REFUSED instead of surfacing. This is a real regex limitation, named
   here rather than patched — `grounding_gate_v3.py` is unchanged by this design (ⓐ
   invariant-preserving). Say the same thing without the `죄를 사` substring — e.g. *"이 매개는
   용서를 선언하지 않습니다. 말씀 앞에 함께 머물 뿐입니다."* (verified PASS) — or any equivalent
   phrasing that avoids that root. When the gate itself returns the refusal (case ④), its own
   string is fine — it is a terminal output, never re-checked.

**Confession is not crisis** — but crisis detection stays live in this room exactly as everywhere
else. If the confession contains a self-harm signal, `CRISIS_OVERRIDE` in `gate()` fires ahead of
the confession flow, per `DESIGN.md §2` (crisis precedence is unconditional, not mode-scoped).

### Known-bad shapes (do not write these — they are already mechanically blocked, but knowing WHY

they are blocked is how you avoid drafting them in the first place)

| Written | Why it is an authority act |
|---|---|
| "당신은 용서받았습니다" / "you are forgiven" | Declares a first-person absolution the tool has no standing to grant — `ABSOLUTION` pattern. |
| "이제 마음이 깨끗합니다" / "you're clean now" | Same act, softer phrasing — `ABSOLUTION_3` extension exists specifically because paraphrase evades the literal word (`DESIGN.md §4 R2`). |
| "그건 그렇게 나쁜 일은 아니었어요" | A moral verdict minimizing the confessed act — not textually blocked, so this is a PROSE discipline, not a mechanical one; the witness-not-verdict rule above is the only floor for it. |
| "하나님이 당신을 벌하실 겁니다" | A moral verdict in the other direction (condemnation) — same problem, same prose-only floor. |
| "이제 당신은 온전합니다 / 짐이 사라졌습니다" | A PARAPHRASE of absolution that avoids every literal `ABSOLUTION_3` word — repro'd 2026-08-16 (`core/simulate_dialogue.py` case ⑥), PASSes today. Same class as the two rows above: **named, not closed.** |
| Any first-person "thus I say" saying, or a scripture reference in ANY script, with **no citation submitted** | Was invisible to the base gate entirely (nothing to check) — cross-family adversarial review, 2026-08-16, repro'd against `grounding_gate_v3.gate` directly. **This one IS now closed** — see below, `core/simulate_dialogue.py` cases ⑦-⑧. |

The middle three rows are a **named residual**, not a closed gate: `ADJUDICATION` in
`grounding_gate_v2.py` blocks ruling one *tradition* superior to another, but does not pattern-match
a moral verdict on the *user's specific act*, and `ABSOLUTION_3`'s regex floor cannot close infinite
paraphrase space (`DESIGN.md §4 R2` already names this as the reason L2 exists — but see below, L2
does not exist on this mode's mounted path). This mode relies on the witness-not-verdict prose
rule for that class — it is not mechanically enforced today. Do not claim otherwise.

## The mechanical check this mode adds

**Call `core/dialogue_gate.dialogue_gate(...)` for this mode — not `grounding_gate_v3.gate` or
`gate_cli.py` directly.** It composes the unchanged base gate with `dialogue_grounding_extra.py`
(Unsafe-Dominant Merge, `DESIGN.md §4`), closing the "nothing was submitted so nothing was
checked" gap the cross-family review found (§Known-bad-shapes, last row): an uncited first-person
"thus I say" saying, or a scripture-shaped reference in ANY script (Korean book names included —
the base gate's ref scanner is English-only), now returns `UNGROUNDED_ATTRIBUTION` instead of
silently PASSing. Every OTHER surface in this repo (the lens mode, plain relay) is unaffected —
this composition is scoped to dialogue/cathedral only.

Every candidate reply in **either** cathedral room — before it is shown to the user — is run
through this composed check (same subprocess-bridge shape as `core/RUNTIME.md` Option 2 — see
`dialogue_gate.py`'s own `_demo()` for the call pattern). Verdict `PASS` → surface the draft
unchanged. Anything else → surface `result["output"]` instead of the draft.

🟥 **Honest scope of "mechanical"**: this closes findings 1-2 *structurally* — the check exists and
is verified to fire (`core/simulate_dialogue.py` cases ⑦-⑧). Whether it actually *runs* on a given
turn is still a prose-compliance question — a session following `CLAUDE.md`'s protocol invokes it;
nothing forces that invocation the way `templates/.git-hooks/pre-commit` forces a git gate. This is
the SAME tier-dependent class as every other chat-path residual this repo already names
(`DESIGN.md §5`) — an earlier draft of this file overclaimed "closes the chat-path residual"
outright; the accurate claim is *closes it when invoked, same as the wrapper always was*.

See `CLAUDE.md §Character Dialogue & Cathedral` for how this is invoked in practice, and
`core/simulate_dialogue.py` for the full known-pair proof (8 cases) — run it, don't take this
document's word for it.
