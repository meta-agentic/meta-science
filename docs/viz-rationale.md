# Evidence page — design rationale

This document is written to be **validated, not admired**: every choice below is stated
with its reason, so an independent reasoner can attack the reasoning rather than the
pixels. The validation verdict lives in `docs/viz-validation.md`.

## Brief

- **Audience**: hackathon judges and technical readers — expert, skeptical, 60 seconds.
- **Purpose**: explanatory, not exploratory. The study is frozen; the story is found.
- **Where**: the deployed Cloud Run service, desktop and phone, light and dark.
- **Task**: verify four claims quickly, then be able to descend to raw data (CSV/JSON).

## The one governing decision

**The page presents the frozen study, plus the live ledger separately.** A paper's
figures come from a dataset that stops moving; mixing live runs into the study figures
would let the evidence drift after the claims were written. So the four figures render
from `static/study.json` — generated once by `scripts/analyse.py --json`, stamped with
git commit and generation time — and the live Firestore totals appear only in a clearly
separated strip below.

## Color: two hues, one meaning each

Blue `#2a78d6/#3987e5` = **concordant with ground truth**. Orange `#eb6834/#d95926` =
**discordant** — refuted predictions, inverted priors, false-positive edges. The same
meaning holds in every figure, so the reader learns the mapping once. The pair passes
all six palette checks in both modes (validator output in the commit). Meaning is never
carried by hue alone — every colored mark also has a direct label or position.

## Figure 1 — Accuracy by arm: strip plot, not a bar of means

- **Relationship**: distribution comparison across 5 ordinal arms.
- **Form**: horizontal strip plot (jittered dots, one row per arm), mean as a heavy tick,
  n=48 labeled per row.
- **Why**: the finding is as much about **variance** as about the mean — lean-25 drops
  the mean 5.4 points and *quadruples the sd*, while its paired twin sits indistinguishable
  from the champion. A bar of means erases exactly the part of the story that matters;
  the skill's own table lists "bar of means alone" as the anti-form for distributions.
  Position on a common aligned scale is the most accurately read encoding
  (Cleveland & McGill).
- **Axis**: 0.4–1.0, *disclosed in the caption*. Dot position is a point encoding, not a
  length encoding, so a non-zero baseline does not lie about ratios — but it is stated,
  not hidden. Accuracy values cluster in 0.8–1.0; a forced zero would crush the
  differences the figure exists to show.
- **Rejected**: box plots (n=48 with heavy ties at 1.0 makes quartile boxes degenerate);
  violins (density smoothing invents shape at this n).
- **Pitfall watched**: overplotting at accuracy=1.0 — mitigated with jitter and 55%
  opacity, so density reads as darkness.

## Figure 2 — Refutation rate by template: sorted horizontal bars

- **Relationship**: ranking of 6 nominal categories.
- **Form**: horizontal bars, sorted by rate, **zero baseline**, counts labeled directly
  (`127/128`), confounded templates annotated with a text badge, not color alone.
- **Why**: ranking task → length on a common scale; horizontal because template names
  are words; sorted by value because the order *is* the story (the two confounded
  topologies at the top refute nearly everything).
- **Rejected**: lollipops (fine, but bars carry the count labels better at this width).

## Figure 3 — Priors on the confounded template: one 100% stacked bar

- **Relationship**: part-to-whole, exactly two parts (94 inverted / 18 confirmed).
- **Form**: a single horizontal 100% stacked bar with counts and percentages labeled on
  the segments, plus the headline stated as text ("5 of 6 priors inverted").
- **Why**: with two parts the whole comparison is one boundary; a stacked bar makes the
  83.9/16.1 split a single length judgment. A pie would be legal at two slices but adds
  an angle judgment for no gain.
- **Pitfall watched**: this is the figure most tempting to over-dramatize. The caption
  says what the population is (112 sign-carrying hypotheses on T6, 48 worlds, champion
  arms) so the denominator is not left to the imagination.

## Figure 4 — Edge recovery: two count bars, derived metrics as annotation

- **Relationship**: magnitude comparison of raw outcome counts.
- **Form**: two horizontal stacked count bars — "edges the agent claimed" (88 true + 24
  false) and "real edges in the worlds" (88 found + 0 missed) — with precision 0.786 and
  recall 1.000 as text annotations beside them, zero baseline.
- **Why**: precision/recall as two abstract bars hides *why* they differ; the raw counts
  show the asymmetry directly — the false-negative segment is visibly absent. Counts are
  the evidence; ratios are derived and belong in the annotation layer.
- **Rejected**: a 2×2 confusion matrix (true negatives are ill-defined over the space of
  absent edges, so two of the four cells would be theater).

## What is deliberately NOT on the page

- No time axis — the study is a frozen cross-section; a trend would be an invention.
- No dual axes, no 3D, no pies with >2 slices, nothing rainbow.
- No Gemini-branded claim on the study figures: the study ran the heuristic ranker, and
  the page says so. Gemini's roles (ranking, proposing, auditing) are stated where they
  actually apply.
- The live strip shows **totals only** (runs, hypotheses, refutations, promotions,
  refusals) — no derived rates, because a live denominator changes under the reader.

## Accessibility gate

- Every hue pairing passes CVD and normal-vision floors (validated, both modes).
- Meaning never in color alone: direct labels on every colored mark.
- Dark mode is selected steps from the same hues, validated against the dark surface.
- A table fallback: every figure's numbers are also in `docs/dataset.md` tables, linked.
- SVG text uses theme ink tokens, never series color.
