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

## What this is not

Not part of the hackathon submission's frozen claims — it lives on a branch, one live
shot per arm, n=1. Before promotion to main it needs: repeated arms (the variance of
one-shot proposals is unmeasured), a free-form family interface to close the menu
leak, and the second law (equal areas needs the observation *dates*, which the blind
arm currently strips — a lovely problem: time itself is identifying).
