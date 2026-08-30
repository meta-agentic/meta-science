# Devpost submission text

## Elevator pitch (200 chars)

An agent that does science on worlds it has never seen — and improves its own method only
when a frozen benchmark proves the improvement real. It can refuse itself.

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
never seen and cannot enumerate. It is promoted only if it beats the incumbent by a
margin — and refused otherwise, with a receipt saying why.

In a representative run, Gemini found a genuine improvement (the same conclusions on a
fraction of the measurement) and it was promoted. It then proposed two further
refinements that *did* score higher, and both were refused for gaining less than the
margin. Refusing marginal gains is the point: it is what stops a system ratcheting
forward on noise.

## How we built it

**Worlds.** Structural causal models seeded from real scientific topologies — state
relations, exponential response, transport chains, compartment flows, inheritance,
confounding. Real science supplies non-trivial structure and known ground truth for free.

**Anonymisation, as a tested property.** Every retrievable surface is stripped at birth:
domain names become `X₁…Xₙ`, labels shuffle per world, constants and exponents randomise,
the functional family varies. Otherwise the agent *retrieves* rather than discovers —
Gemini already knows the gas laws and would emit one on recognising the shape, then design
experiments confirming what it had already said.

**The gate.** `raw → wiki → output`, where the tier a record sits in *is* its status.
Gemini proposes; it never sees the held-out seeds, never runs the scorer, and never
writes to canon. The gate computes the evidence itself.

**Google stack.** Gemini 3.6-flash (falling back to 3.5-flash) through the GenAI SDK
drives both reasoning roles. Firestore holds the ledger. Cloud Run executes runs. All of
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

**Proving anonymisation rather than asserting it.** Checking that banned words are absent
is easy. The real question is whether a model can answer without experimenting. So we
tested it adversarially — and it cannot.

## Accomplishments

The measurement that settles the whole design:

| | confounded worlds recovered |
|---|---|
| Gemini, observation only | **0 / 4** |
| The same loop, allowed to intervene | **4 / 4** |

Identical worlds. The only difference is the ability to act. That single comparison shows
the anonymisation holds *and* that intervention is doing real work rather than decorating
a conclusion the model already had.

## What we learned

That the hard part of a self-improving system is not the improving. It is building the
evidence the improvement has to survive — and then not letting the proposer anywhere near
it.

## What's next

Open-ended generations rather than the single demonstrated turn; non-linear effect
estimation so genuinely multiplicative worlds are not approximated; and a larger held-out
set so smaller margins become measurable.

## Built with

`python` · `gemini-3.6-flash` · `google-genai` (GenAI SDK) · `google-cloud-firestore` ·
`cloud-run` · `secret-manager` · `terraform` · `fastapi` · `docker` · `pytest`

## What we are not claiming

Automated scientific discovery has substantial prior art — active learning, causal
discovery, rule-induction in the Zendo/Eleusis tradition. This is not the first AI
scientist and does not claim to be. The narrower claim is falsifiable self-improvement: a
loop whose every promotion is earned against evidence the proposer cannot see, score, or
tune against, leaving a receipt either way.
