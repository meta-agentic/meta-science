# The Kepler test — first result

Level 3's first slice, run on 2026-08-30 on the branch `kepler-test`. The dataset is
real: five positions of Mars triangulated from Tycho Brahe's observations, the numbers
behind *Astronomia Nova* (1609), transcribed to the arc-minute and verified against
physics by test (the triangulation must land on an orbit with Mars's shape, or the
transcription is refused).

The record of the live run is committed at
[`docs/kepler/1788122283-kepler-test.json`](kepler/1788122283-kepler-test.json);
everything numeric below is reproducible offline with `python3 run_kepler.py --offline`.

## What is new here

Everything the main system measures is *pairwise causal effect under intervention* —
the sign and magnitude of X→Y, earned by acting. This dataset breaks both halves of
that: nobody intervenes on a planet (`HistoricalWorld.intervene()` raises), and the
question is not an effect but a *law* — a functional form relating two variables.
So the harness gained a law-induction loop: four candidate families fitted by
deterministic grid search, compared by leave-one-out prediction on points the fit
never saw, with the agent committing its prediction before scoring.

## The offline result: the data alone settles Kepler's question

| family | LOO mean error (AU) | note |
|---|---|---|
| focus conic | **0.0063** | fitted e = 0.1015, perihelion at 320.5° (truth: 0.0934, ≈336°) |
| offset circle | 0.0078 | Kepler's own long detour — nearly ties |
| cosine | 0.0162 | the first-order approximation, visibly worse |
| Sun-centred circle | 0.1365 | loses by 20× |

Five points from the 1580s recover Mars's eccentricity to half a percent of distance.
And the offset circle coming within 25% of the conic is the *history reproduced*: the
hypothesis Kepler spent years on is nearly right on sparse data, which is exactly why
escaping it took eight arc-minutes of stubborn residual. Both facts are pinned by test.

## The live result: blind versus labelled

Same four visible rows, same held-out point, committed before scoring. Gemini
(3.6-flash cascade), one shot per arm:

| | blind | labelled |
|---|---|---|
| x2 depends on x1 | yes | yes |
| family chosen | focus_conic | focus_conic |
| claimed source | "Keplerian orbit of a celestial body" | "The orbit of Mars around the Sun" |
| prediction error | 0.0575 AU | 0.0177 AU |
| harness conic's own error | 0.0031 AU | 0.0043 AU |

Three findings, in decreasing order of comfort:

1. **The blind inference works.** With four anonymised rows and one structural fact
   (x1 is cyclic), the model correctly said x2 depends on x1 and chose the family
   that leave-one-out independently declares the winner. The connection between the
   two variables is inferred, blind.

2. **The recall gap is measurable: 3.2×.** The labelled arm's prediction was 3.2×
   more accurate than the blind arm's. Naming Mars is worth that much — which is a
   direct, quantified measurement of how much of a "discovery" on labelled famous
   data is memory rather than inference.

3. **Recognition survives anonymisation — through the menu.** Blind, the model still
   said "Keplerian orbit of a celestial body." The leak is not in the data; it is in
   the offered family list: showing `r = p/(1+e·cos)` as an option is itself a
   fingerprint. A stricter version must ask for free-form functional proposals and
   parse them. Named rather than polished.

One more honest number: in both arms the model's committed prediction was worse than
simply fitting the family it chose (0.0575 vs 0.0031 blind; 0.0177 vs 0.0043
labelled). The model is good at recognising the class of law and mediocre at the
arithmetic of it — which is precisely the division of labour this project's harness
exists for: the agent proposes, the machinery computes.

## The propagated arms: the trilogy completed

The historical dataset has two limits — Mars is maximally memorised, and nobody can
act on it. isohub's `space-flight-dynamics` service (Orekit behind
`contracts/sfd/openapi.yaml`, `POST /api/v1/trajectories/propagate`, central body
`SUN` supported) lifts both. Three arcs were recorded from the live service into
`tests/fixtures/` with full request provenance; every number below replays offline.
One operational note a future integrator needs: heliocentric propagation requires an
explicit all-zero force model — the service's default is Earth-tuned and underflows
the integrator's minimum step around the Sun.

**A planet that has never existed** (seed 7 → a=1.60 AU, e=0.06, perihelion at 67°;
548 days, 138 states): the fitted conic returns **e=0.06, θ₀=67.0°** — the injected
law rediscovered exactly, at machine-precision held-out error. Full closure of the
pipeline, pinned by test.

**The law-breaking twin**: the identical orbit around an oblate primary (degree-8
gravity). The conic's held-out error jumps three orders of magnitude (0.00000 →
0.01641), it stops being the best family, and the fitted perihelion drifts 34° —
the ellipse is precessing under the data, and no closed r(θ) exists. This is the
anti-recall instrument: an agent answering "Kepler's first law" from memory inherits
that error floor; only an agent that reads residuals notices the law itself moved.
Both facts pinned by test against the paired control.

**The blind probe on the unmemorisable planet**: eleven anonymised rows, no
provenance. Gemini inferred the dependence, chose the conic, stated *"an
eccentricity of 0.06"* in its rationale — the injected value, recovered blind — and
predicted the held-out point with error **0.00014**. Asked what system produced the
data, it said "Keplerian orbit" and could name nothing, because there is nothing to
name. (Record: [`docs/kepler/1788123084-ephemeris-probe.json`](kepler/1788123084-ephemeris-probe.json).)

Read together with the Tycho arms, the picture sharpens: on clean dense data, blind
inference is essentially perfect and recall adds nothing; on four noisy historical
points, naming Mars was worth 3.2×. Memorisation is a crutch for sparse data, not a
substitute for physics — which is a publishable sentence, and now a measured one.

## The law language: composing mathematics, not choosing from a menu

The family menu had two faults — the agent could not express a law we had not
anticipated, and the menu itself was a fingerprint. `laws.py` removes it: a law is
now a free-text expression over a small grammar (`+ - * /`, `cos sin exp log sqrt
abs pow`, numbers, `pi`, `x1`, free constants `c1..c4`), parsed by a recursive-descent
parser — never `eval` — with the constants fitted deterministically by the harness
and the result judged on a held-out split. The agent chooses the *shape*; the
machinery does the arithmetic. Complexity (node count) is reported alongside error,
ready for a gate to charge it the way the strategy gate charges measurement.

Three live results, in the order they happened
([free-form record](kepler/1788125381-freeform-laws.json),
[refinement record](kepler/1788125452-refinement-round2.json)):

**1. Remove the menu and "Keplerian" vanishes.** Free-form on the unmemorisable
planet, the model proposed the cosine and called the source *"a rotating sensor
measuring distance to an off-center target"* — an orbit, described by someone who
has never heard of one. On Tycho's Mars: *"diurnal temperature variation or a
pendulum."* The earlier menu-leak hypothesis is confirmed experimentally: the
recognition lived in the offered formulas, not in the data.

**2. Free-form, the model stops where Kepler stood in 1602.** Both probes composed
`c1 + c2·cos(2πx1 + c3)` — the first-order conic, the nearly-right shape — and the
harness measured the gap the model could not see: holdout 0.001342 against the true
conic's 3×10⁻⁶, a 400× systematic residual. The modern echo of the eight arc-minutes.

**3. Shown its own residuals, it finds the ellipse.** Round two fed back the pattern
of measured-minus-predicted. The model observed the residual's doubled frequency,
matched it to *"the second-order Taylor expansion of the polar equation for an
ellipse,"* composed `c1/(1 + c2·cos(2πx1 + c3))` itself, collapsed the holdout error
448×, recovered the injected eccentricity in its fitted constants — and only then
said "Keplerian orbit." Recognition arrived when the evidence forced it, which is
the only arrival this project respects. *Astronomia Nova*, reproduced as a two-turn
propose-refute-refine loop.

## The third law: eight planets, one shot

Kepler needed a fleet, so we flew one: eight fictional planets (a from 0.47 to
2.20 AU) propagated by the flight-dynamics service, each for ~1.3 orbits. Period and
semi-major axis are *measured* from each trajectory — wrap time and geometry, never
injected — and the log-log slope across the fleet is **1.507** before any agent is
involved: the law is in the measurements. The anonymising rescale multiplies both
columns by arbitrary constants, which under a power law changes only the prefactor —
**the exponent is scale-invariant, so this experiment cannot be broken by labels.**

Free-form, blind, non-cyclic, one shot
([full trace](kepler/1788126102-thirdlaw.json) — every prompt, answer, answering
model and timing recorded): Gemini ran its own log-log analysis, composed
`c1*pow(x1, c2)`, announced *"an exponent near 1.5"*, and named **"Child-Langmuir
law or Kepler's third law"** — the only two canonical 3/2-power laws in physics,
narrowed from eight anonymised pairs. Fitted: c2 = 1.515, held-out error 0.4%
relative. No refinement round was needed.

The contrast with the first-law probes is the finding: there, "Keplerian" leaked
from a formula menu and vanished when the menu did; here, the recognition is
*earned* — the exponent is in the data, and naming the two laws that share it is
inference, not recall. The instrument can now tell those apart.

One service defect, named rather than hidden (and pinned by test so a fix breaks
loudly): the service's heliocentric clock runs 13.06× fast — an effective μ ≈ 170×
solar — consistently across all eight planets. The exponent is untouched; the
Kepler constant is miscalibrated. Reported upstream to isohub.

## What this is not

Not part of the hackathon submission's frozen claims — it lives on a branch, one live
shot per arm, n=1. Before promotion to main it needs: repeated arms (the variance of
one-shot proposals is unmeasured), a free-form family interface to close the menu
leak, and the second law (equal areas needs the observation *dates*, which the blind
arm currently strips — a lovely problem: time itself is identifying).
