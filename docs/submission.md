# Devpost submission text

## Elevator pitch (200 chars)

Hypothesis: a model can improve its own scientific method. Thesis: nothing counts
until it beats the champion, by a margin, on worlds it cannot see. We built that
gate — it refused Gemini twice.

## Inspiration

"Self-improving agent" is the most common unfalsifiable claim in this field. Every demo
shows successes, which proves nothing: a system that *reports* it improved is
indistinguishable from one that logs `"improved!"` and changes nothing.

We wanted to build the version that can be checked — where the interesting artefact is
not a system that improves, but one that **refuses to.**

## What it does

An agent meets a world it has never seen: variables with opaque names, no documentation,
and two affordances — look, or act. It forms a falsifiable hypothesis, designs its own
intervention, runs it, and finds out it was wrong.

Then it does the same thing one level up. It proposes a change to its own
experiment-design strategy, and that proposal is evaluated on 24 held-out worlds it has
never seen and cannot enumerate. It is promoted
only if it beats the incumbent strategy by a margin — and refused otherwise, with a receipt saying why.

In a representative run, Gemini found a genuine improvement (the same conclusions on a
fraction of the measurement) and it was promoted. It then proposed two further
refinements that *did* score higher, and both were refused for gaining less than the
margin. Refusing marginal gains is
the point: it is what stops a system ratcheting forward on noise.

One number up front: reading observations alone, Gemini recovers the causal structure of
0 of 4 confounded worlds; the same loop, allowed to intervene, recovers 4 of 4.

## How we built it

**Worlds.** Structural causal models seeded from real scientific topologies — state
relations, exponential response, transport chains, compartment flows, inheritance,
confounding. Real science supplies non-trivial structure and known ground truth for free.

**Anonymisation, as a tested property.** Every retrievable surface is stripped at birth:
domain names become `X₁…Xₙ`, labels shuffle per world, constants and exponents randomise,
the functional family varies. Otherwise the agent *retrieves* rather than discovers —
Gemini already knows the gas laws and would emit one on recognising the shape, then design
experiments confirming what it had already said.

**The gate.** Every record lives in one of three tiers — `raw` (anything the agent
produces), `wiki` (candidate findings), `output` (accepted canon) — and a record's tier
*is* its status: nothing is promoted by assertion, only by moving up. Gemini proposes;
it never sees the held-out seeds, never runs the scorer, and never writes above `raw`.
The gate computes the evidence itself.

**Google stack.** Gemini 3.6-flash (falling back to 3.5-flash) through the GenAI SDK
drives both reasoning roles — the scientist that experiments and the proposer that
suggests method changes. Firestore holds the ledger of every verdict. Cloud Run executes runs. All of
it declared in Terraform, with the API key in Secret Manager and a service account scoped
to `roles/datastore.user`.

## Challenges

**We built a metric we could have gamed.** Cost initially charged the number of
experiments, which left sample size free — so a challenger could buy accuracy by drawing
more data and appear to have learned something. One did exactly that. Cost now charges
total measurement, and that candidate loses. Gemini independently reached the same
conclusion our parameter sweep did: *"accuracy is saturated, reduce measurement cost."*

**A silent failure that looked like an empty answer.** The model cascade caught every
exception and moved on, so a `503 UNAVAILABLE` from `gemini-3.7-flash` surfaced as a
model with nothing to say. Failures are now recorded, and only a transient overload is
retried.

**An auditor that flagged everything.** We added a second Gemini model to check whether
each promotion was earned rather than gamed. It initially flagged every single
promotion — which carries exactly as much information as flagging none. The fix was not a
better prompt but a better receipt: the score is now reported as separate accuracy and cost components, so
"spent less and kept the answers" is distinguishable from "spent less and lost accuracy" —
with an explicit noise floor marking movements small enough to be sampling variation. It now separates
the two cases it exists to separate.

**Receipts that did not replay.** A test pinning the README's figures to the code failed
the first time it ran, and the cause was worse than a stale number: world generation was
seeded with Python's builtin `hash()`, which is randomised per process. The same seed built
a different world in every run, so the replayability the receipts promise did not hold and
a judge would have got different numbers than we published. Fixed with a stable hash, and
determinism is now asserted in a subprocess — an in-process check cannot see it.

**Proving anonymisation rather than asserting it.** Checking that banned words are absent
is easy. The real question is whether a model can answer without experimenting. So we
tested it adversarially — and it cannot.

## Accomplishments

The measurement that settles the whole design — four worlds with a hidden confounder,
scored on whether the agent recovers the true causal structure:

| | confounded worlds recovered |
|---|---|
| Gemini, observation only | **0 / 4** |
| The same loop, allowed to intervene | **4 / 4** |

Identical worlds. The only difference is the ability to act. That single comparison shows
the anonymisation holds — if Gemini could recognise these worlds, observation alone would
have sufficed — *and* that intervention is doing real work rather than decorating a
conclusion the model already had.

**Our benchmark was flattering us, so we changed it.** Late on we checked whether the two
arms of an intervention — the treated and untreated runs — share random draws. They did — common random numbers, which makes
the paired difference isolate the causal effect. Elegant, and a trap: with the noise
cancelled, estimates stay precise however few samples are drawn, so cutting measurement
was free score. That is very likely why the proposer kept winning by asking for fewer
samples. We measured both regimes: at 25 samples per arm, accuracy holds at 98.2% under
shared noise but falls to 84.3% under honest, independent noise. Independent noise is now the default, the extreme
strategy correctly loses, and the promotion the demo shows survives the harder regime.
Both facts are asserted by tests.

## What we learned

That the hard part of a self-improving system is not the improving. It is building the
evidence the improvement has to survive — and then not letting the proposer anywhere near
it.

## What's next

Level 3 — after level 1 (do science) and level 2 (improve the method) — is open-ended,
repeated self-evolution scored on *law recovery under replication*. Every hypothesis is
replicated across fresh seeds, with verdicts by meta-analysis, and the model proposes
functional forms rather than effect sizes. The promotion gate then does for many
generations what it does today for one: margins against noise-ratcheting, an independent
auditor against metric-gaming, receipts for the whole lineage, and ever-fresh generated
worlds as the pre-registration analogue that keeps repetition from becoming p-hacking. Plus the smaller debts: non-linear effect estimation, and a larger
held-out set so smaller margins become measurable.

## Built with

`python` · `gemini-3.6-flash` · `gemini-3.5-flash-lite` · `google-genai` (GenAI SDK) · `google-cloud-firestore` ·
`cloud-run` · `secret-manager` · `terraform` · `fastapi` · `docker` · `pytest`

## What we are not claiming

Automated scientific discovery has substantial prior art — active learning, causal
discovery, rule-induction in the Zendo/Eleusis tradition. This is not the first AI
scientist and does not claim to be. The narrower claim is falsifiable self-improvement: a
loop whose every promotion is earned against evidence the proposer cannot see, score, or
tune against, leaving a receipt either way.
