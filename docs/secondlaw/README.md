# The second law — swept areas, timestamps, and the test that finally bites

Run on the `second-law` branch, 2026-08-31, from three arcs recorded off the live
flight-dynamics service (full request provenance in `tests/fixtures/`, all analysis
replayable offline). Full Gemini traces: [`1788127371-secondlaw.json`](1788127371-secondlaw.json);
the extrapolation table: [`secondlaw-extrapolation.json`](secondlaw-extrapolation.json).

## The instrument

`swept_area()` accumulates the radius vector's chord triangles; `areal_rates()` is the
per-interval sweep — the quantity Kepler's second law says is constant. Measured drift,
first decile to last:

| world | areal-rate drift |
|---|---|
| fictional planet, two-body (P28D/PT6H) | **−0.003%** |
| LEO control, two-body (P5D/PT5M) | −0.008% |
| same LEO + atmospheric drag, 100 m² | **−1.107%** |

Equal areas holds where it should and dies under dissipation — 140× the control's
drift, same orbit, one force-model field different (asserted by test on the stored
requests). Two lessons are pinned as tests: sampling must respect the clock (an early
probe stepping 2 h across a 93-minute orbit produced plausible aliased nonsense), and
**oblateness cannot break this law** — J2 is axially symmetric, equatorial angular
momentum is conserved; breaking Kepler II takes a non-central, dissipative force.

## The agent, blind — two rounds, both arms

Same protocol per arm: free-form law on (time, swept area), then a residual review
where the correct move differs — arm A's residuals are noise-shaped (keep), arm B's
are structure (refine).

**Arm A (law holds).** Round 1: `c1*sin(c2*x1)` with tiny `c2` — linear in disguise
("simple harmonic oscillator"). Its own residuals betrayed the sine's cubic error;
round 2 added the linear term and the fit collapsed onto it: `c3 = 0.871` carrying
everything, the sine amplitude vestigial at `0.0004`, holdout 4 ppm. Numerically the
model converged to the second law; structurally it kept a decorative term that a
complexity-charging gate (the MDL cost `laws.py` already reports) would shave off.
The claimed sources stayed fanciful — the mathematics arrived, the physics never did.

**Arm B (law broken).** The model detected the sublinearity blind — the break was
found. But it reached for saturating families both rounds (capacitor charging, then
tanh, "terminal velocity"), and the truth is not saturation: it is a linear sweep
losing 1.1% of its rate — linear minus a small quadratic. On interleaved holdout the
tanh looks excellent (0.06% relative). It is wrong anyway, and one split exposes it:

## Fit early, judge late

Fitted on the first 60% of the drag arc, judged on the final 20% — extrapolation in
time, the only regime a law actually promises anything about:

| candidate | future error |
|---|---|
| linear − quadratic (the true shape) | **0.0039** |
| pure linear (naive Kepler II) | 0.0218 |
| Gemini round 2 (tanh) | 0.0880 |
| Gemini round 1 (capacitor) | 0.1960 |

Both model shapes that flattered on interleaved holdout collapse 22–50× when asked
about the future; the honest shape wins by an order of magnitude. **Interleaved
holdout rewards interpolation; a law is a claim about extrapolation.**

## The finding, applied — and the metric's own bug, found by its first test

`laws.judge()` now scores every law twice — interleaved (interpolation) and
fit-early/judge-late (extrapolation) — and issues an `extrapolates` verdict. The law
loop (`freeform_probe`, both runners) judges through it, and the third-law runner's
refinement round now triggers on a failed extrapolation verdict, not on a flattering
interpolation number.

Calibrating the verdict on this experiment's own data immediately broke the naive
design. The first criterion was a pure self-ratio — future error over interleaved
error — and the **true shape failed it** (penalty 8.1): a law that interpolates
near-perfectly can have a future error many times its interleaved error that is
still 0.08% of the data. A self-ratio punishes excellence. The shipped criterion
takes the more generous of two bounds — 3× the interleaved error, or 0.1% of the
data's own scale ([verdicts](judge-verdicts.json), pinned by test):

| candidate | interleaved | future | penalty | extrapolates |
|---|---|---|---|---|
| true shape (linear − quadratic) | 0.00048 | 0.00393 | 8.1 | **yes** |
| naive linear | 0.00527 | 0.02184 | 4.1 | no — misses the decay |
| Gemini r2 (tanh) | 0.00563 | 0.08811 | 15.6 | no |
| Gemini r1 (capacitor) | 0.03124 | 0.19622 | 6.3 | no |

## The re-run under the judge (trace: [`1788129198-secondlaw.json`](1788129198-secondlaw.json))

Same protocol, scored through `laws.judge()` — and all four cells moved:

**Arm A, round 1** — the identical sine-in-disguise as the first run (deterministic
fit, same constants), but now the verdict exposes on sight what the old scorer could
not: interleaved 0.011 looks healthy, future error 0.109, penalty 9.6 —
**extrapolates: False**. Round 2's repair (adding the linear term) passes through the
absolute floor exactly as designed: a 39× self-ratio on a 4×10⁻⁵ interpolation is
excellence, not overfitting.

**Arm B, round 1** — a different and better proposal this time: the rational shape
`x1/(c1 + c2·x1 + c3·x1²)` ("enzyme kinetics, Haldane/Andrews"). Expanded to second
order this *contains* the true linear-minus-quadratic behaviour, and the judge
certifies it: interleaved 0.0001, future 0.0014, **extrapolates: True** — a 60×
better future error than the previous run's tanh, which the judge would have refused.

**Arm B, round 2 — the first observed "keep."** Shown its residuals, the model
declined to refine: *"oscillatory behaviour without a clear systematic trend,
indicating they are measurement noise."* Correct — and the refusal option is what
makes every refinement elsewhere informative. In the first run the model changed its
law in all four opportunities; under this run's protocol it held when holding was
right.

One honest boundary: the judge certifies extrapolation over the recorded horizon,
not to infinity — the rational shape's far asymptote (a decaying sweep) is wrong
beyond x1 ≈ 44, twenty times past the data window, where no finite evidence reaches.
A law survives its tests; it is never proven by them. The claimed sources, as ever,
wandered (pendulum → rolling wheel; Haldane → Langmuir): the mathematics converges
long before the physics naming does.

## Standing caveats

n=1 per arm, one model family, and the anonymisation-of-time problem remains open for
*real* datasets (these are synthetic, so elapsed time carries no identity; Tycho's
dates would). Same status as the rest of the branch: evidence for the article, not
claims for the hackathon submission.
