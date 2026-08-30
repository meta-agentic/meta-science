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
holdout rewards interpolation; a law is a claim about extrapolation.** The law loop's
scoring should split in time, not in stride — that change is the first item this
experiment feeds back into the harness.

## Standing caveats

n=1 per arm, one model family, and the anonymisation-of-time problem remains open for
*real* datasets (these are synthetic, so elapsed time carries no identity; Tycho's
dates would). Same status as the rest of the branch: evidence for the article, not
claims for the hackathon submission.
