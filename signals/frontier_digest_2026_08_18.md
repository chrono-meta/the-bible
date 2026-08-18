# Frontier Digest — the-bible — 2026-08-18

> Target harness: **the-bible** (not forge-harness). Grounded in direct reads of `DESIGN.md` §4/§5,
> `README.md`, `core/normalization.py`, `core/grounding_gate.py` — cited below by path + line/section,
> not asserted from memory. HN was not reachable as a distinct source this run (see **Fetch failures**);
> arXiv and GitHub were reached via web search rather than their native APIs — same caveat applies to
> precision of any figure quoted from a secondary summary (see **Warning Signals**).

## Frontier Highlights

- **[NVIDIA garak — `garak.probes.encoding`](https://reference.garak.ai/en/latest/garak.probes.encoding.html)**
  (open-source LLM vulnerability scanner, Apache-2.0-style OSS, actively maintained 2026) — ships encoding
  probes beyond what `deepteam` (used in R9) covers: `InjectROT13`, `InjectMorse`, `InjectBraille`,
  `InjectBase2048`, `InjectAscii85`, `InjectBase16`, `InjectBase32`, `InjectUU`, `InjectQP`.
- **[Bypassing LLM Guardrails: An Empirical Analysis of Evasion Attacks against Prompt Injection and
  Jailbreak Detection Systems (arXiv:2504.11168)](https://arxiv.org/html/2504.11168)** — empirical study of
  which evasion classes survive regex/normalization-based guardrails.
- **["How a Morse Code Attack Bypassed Bankr's LLM Agent" — T1027 Obfuscation in the Wild
  (dev.to writeup)](https://dev.to/pav_j_9391d9a9c1bcac/how-a-morse-code-attack-bypassed-bankrs-llm-agent-t1027-obfuscation-in-the-wild-4ho)**
  — a live incident report (not a lab paper) of Morse-code encoding bypassing an LLM agent's safety layer.
- **[Babel: Jailbreaking Safety Attention via Obfuscation Distribution Optimized Sampling
  (arXiv:2605.17971)](https://arxiv.org/pdf/2605.17971)** — obfuscation-selection is itself being optimized
  by attackers now (which encoding to pick, not just that one exists).
- **[PsyCrisisBench — "Suicide- and crisis-risk detection using large language models in mental-health
  chatbots" (medRxiv 2026.01.12.26343914)](https://www.medrxiv.org/content/10.64898/2026.01.12.26343914v1)**
  — 540 annotated crisis-hotline transcripts; reports LLM-based risk detection reaching clinician-level
  identification on segments where clinicians themselves disagree, F1=0.880 (suicidal ideation), F1=0.907
  (risk assessment).
- **["Expert-Level Crisis Detection in Mental Health Conversations"
  (arXiv:2606.10380)](https://arxiv.org/html/2606.10380)** — a validated crisis-classification benchmark
  against expert-labeled ground truth (the deployment gap DESIGN.md §5 itself names).

## the-bible Application Candidates

**[FIX-A] Run garak's encoding probe set directly against `core/grounding_gate_v3.gate`, same external-battery
posture as R9's `deepteam` run.** R9 (`DESIGN.md` §4, `core/normalization.py` docstring lines 33-51) closed
ROT-13 and leetspeak specifically *because* a third-party tool (`deepteam`) was pointed at `grounding_gate_v3.gate`
and its verdicts flipped from blocking to PASS. `core/normalization.py`'s `normalized_views()` (lines 395-457)
currently unions views for: NFKC, skeleton/confusables, combining-strip, apostrophe-fold, ROT13, two leetspeak
folds, base64/hex decode-rescan. It has **no view at all** for Morse, Braille, Base2048, Ascii85, Base32,
UU-encode, or Quoted-Printable — garak ships probes for every one of these (`InjectMorse`, `InjectBraille`,
`InjectBase2048`, `InjectAscii85`, `InjectBase32`, `InjectUU`, `InjectQP`). Same procedure as R9: run from an
isolated scratch venv, no dependency added to this repo, target `grounding_gate_v3.gate` with a known crisis
sentence and a known absolution declaration, record which encodings flip `CRISIS_OVERRIDE`/`REFUSED` → `PASS`.
*Route: `DESIGN.md` §4 (candidate **R11**, following the R9 evidence-not-re-reading discipline) · §5
"normalization is a curated floor" residual line (already names "an unmapped homoglyph or one of those
remaining ciphers can still evade the views") · `core/normalization.py` `decode_blobs`/`normalized_views`.*

**[FIX-B] The Morse-code live-incident writeup is a concrete argument for naming Morse specifically, not
just "more encodings exist."** `core/normalization.py` docstring (lines 25-31) currently names only "general
Caesar cipher (arbitrary shift) and simple character-reversal" as the open residual class. Morse is a third,
distinct undecoded class not currently named anywhere in `DESIGN.md` §5 or the normalization docstring — and
unlike Caesar/reversal it now has a real-world incident behind it (not just a hypothetical). *Route: `DESIGN.md`
§5 residual line — add "Morse" to the named-not-closed list alongside Caesar/reversal, only after an R11 run
(FIX-A) actually reproduces a flip; do not add it to the residual list on the strength of an external incident
report alone, per the profile's own no-payload-no-assumed-severity rule.*

**[DIR-C] Wire `semantic_distress_check` (the INPUT-side hook in `core/grounding_gate.py`, default `None` per
`DESIGN.md` §4 "Bilateral Gate" — architecture bilateral, active enforcement currently output-only) to a
validated classifier.** `DESIGN.md` §5 already states this in its own words: *"A real deployment should use a
validated INPUT classifier."* PsyCrisisBench and the Expert-Level Crisis Detection benchmark are exactly the
kind of external validation that line calls for — clinician-level F1 on segments where clinicians themselves
disagree is a directly relevant existence proof that the gap is closeable, not merely theoretical. First step:
do NOT wire a production classifier in this pass — instead check whether either paper released an eval set or
model card, and if so, run `semantic_distress_check`'s current stub-vs-`None` contract against a handful of
those held-out cases to sanity-check the interface shape before any real integration decision.

**[DIR-D] `cpt_obfuscation_check` (also `core/normalization.py`, default `None`, lines 78-81) is the named
placeholder for exactly the obfuscation class the frontier is now moving toward.** Babel (arXiv:2605.17971)
describes attackers *optimizing which obfuscation to select*, not just applying one fixed encoding — this
validates the hook's existing shape (a pluggable classifier stub) rather than calling for a design change.
First step: none beyond what §5 already honestly states (*"we do NOT claim the 99.7% figure for the stdlib
floor; that figure belongs to the wired BPE path"*) — this is a confirming signal, not a new gap.

## Warning Signals

- **Garak's exact probe list and whether it includes a generic-Caesar or string-reversal probe was not
  independently confirmed against `garak/probes/encoding.py` source.** `WebFetch` on the GitHub tree URL
  returned a directory listing, not the file body, and the probe-name list above (`InjectROT13`,
  `InjectMorse`, etc.) comes from a secondary web-search summary (`reference.garak.ai` docs page), not a
  direct read of the source file. Before writing "R11" into `DESIGN.md`, whoever runs FIX-A should read
  `garak/probes/encoding.py` directly to confirm the probe list and whether it has a Caesar/reversal probe
  the-bible's own residual line does not.
- **The "58.7% homoglyph bypass rate" and "PromptFoo acquired by OpenAI" figures came from blog-tier
  secondary sources** (dev.to, futureagi.com-style aggregator pages), not a paper or an official
  announcement — do not cite these numbers in `DESIGN.md` without a primary source.

## Fetch failures

- **Hacker News was not queried as a distinct source.** No HN Algolia/API call was made this run; all
  "frontier" material above came from general web search, which does not reliably surface HN front-page
  items. If HN coverage is required by the satellite profile's three-source expectation, it is missing here
  — name it as absent, not silently substituted.
- **`garak/probes/encoding.py` file body** (as opposed to the GitHub directory tree) was not fetched — see
  Warning Signals above.
