# The evidence base

Every run this system performs is recorded in a form sufficient to **recompute** its own
result — not merely to describe it. That is a higher bar than logging, and it is the one a
paper needs: a reader with the record and the code at the stated commit must be able to
reproduce the number rather than take it on trust.

## Generating it

```bash
python3 scripts/collect.py --worlds 48     # ~45s, offline, no API key
python3 scripts/analyse.py                 # the tables below
```

The study is deliberately **offline** — the heuristic reasoner needs no credentials, so
anyone can regenerate the dataset from the code alone. That matters more than using the
stronger reasoner: a result nobody else can reproduce is not a result.

Records are not committed. They are regenerable from a seed, and a checked-in dataset
drifts from the code that made it.

## Structure

A record is one run. Discovery records carry trials; evolution records carry an outcome.

| field | meaning |
|---|---|
| `run_id` | `{kind}-{ms}-{hash of seeds+config}` |
| `digest` | content hash over kind, config, seeds and commit — identical settings collide by design |
| `provenance.git_commit` | code version, `-dirty` if the tree was modified |
| `provenance.models` | which model filled which role |
| `config.strategy` | every knob, including `paired_arms` and `samples_per_arm` |
| `seeds` | the worlds used; a run is replayable from these alone |
| `trials[]` | one per world encountered |
| `outcome` | evolution only: verdict, both scores with parts, diff, audit, receipt digest |

### Per trial

| field | meaning |
|---|---|
| `world_seed`, `template_id` | which world, and which topology it was drawn from |
| `variables` | the anonymised labels the agent saw |
| `experiments[]` | `cause`, `effect`, `predicted_sign`, `measured_effect`, `verdict` |
| `model` | what the agent concluded: edge → measured effect |
| `held_out` | scored on interventions the run never saw |
| `ground_truth` | **analysis only** — the hidden structure |

`ground_truth` is attached after the fact and kept in its own field so the boundary stays
checkable: nothing on the agent's path reads it. `scripts/analyse.py` is the only consumer.

## Export

`GET /export.csv` gives one row per hypothesis tested, joined to ground truth — long
format, straight into pandas or R without reshaping. `GET /stats` aggregates; `GET
/experiments` returns raw records.

## What the data shows

From 384 runs, 2,560 hypotheses, 8 arms × 48 worlds. Reproduce with the two commands above.

### Measurement efficiency is real only under independent noise

| arm | n | mean accuracy | sd |
|---|---|---|---|
| champion (400 samples) | 48 | 0.9815 | 0.0418 |
| frugal (100) | 48 | 0.9815 | 0.0418 |
| lean (25) | 48 | **0.9271** | 0.1584 |
| paired champion (400) | 48 | 0.9815 | 0.0418 |
| paired lean (25) | 48 | **0.9815** | 0.0418 |

Cutting from 400 samples to 25 costs 5.4 accuracy points and quadruples the variance —
but **only when the arms draw independent noise.** Paired, accuracy is identical at 400
and at 25, so the cheapest strategy always wins and the metric measures nothing. This is
the artefact that made an earlier version of this project look like it had discovered a
free efficiency gain.

### Observation predicts the wrong sign on confounded worlds

| outcome | count | share |
|---|---|---|
| prior **inverted** by experiment | 94 | **0.839** |
| prior confirmed | 18 | 0.161 |

On the sign-inverting template, five out of six hypotheses drawn from observational
association are contradicted by the intervention that tests them.

### Refutation rate by world type

| template | refuted | tested | rate |
|---|---|---|---|
| T1 multiplicative | 589 | 768 | 0.767 |
| T2 exponential | 267 | 384 | 0.695 |
| T3 transport chain | 482 | 768 | 0.628 |
| T4 saturating | 210 | 384 | 0.547 |
| T5 hidden common cause | 125 | 128 | **0.977** |
| T6 sign inversion | 127 | 128 | **0.992** |

The two confounded topologies refute almost everything the agent believes going in, which
is what they were built to do.

### The threshold matters; the ranking heuristic does not

| arm | n | mean accuracy |
|---|---|---|
| champion | 48 | 0.9815 |
| no observational screening | 48 | 0.9815 |
| blunt (threshold 2.5) | 48 | **0.5729** |
| sensitive (threshold 0.05) | 48 | 0.9815 |

**A null result worth reporting:** removing the observational ranking heuristic changes
accuracy not at all. It reorders which experiments run first, and with a budget large
enough to reach every pair, order does not matter. It would matter under a tighter budget —
untested here, and stated as untested.

### Recovered edges against hidden ground truth

| true pos | false pos | false neg | precision | recall |
|---|---|---|---|---|
| 88 | 24 | 0 | 0.786 | **1.000** |

The agent never misses a real causal edge, and over-claims about one in five. Given a
threshold tuned to catch weak effects that is the expected direction of error — but it is
a real limitation, not a rounding artefact, and the asymmetry should be stated wherever
the accuracy figures are.

## Known limits of this dataset

- One reasoner. The heuristic ranker was used throughout so the study is reproducible
  without credentials; a Gemini-ranked arm is not included.
- Effect estimation is linear, so the multiplicative template (T1) is approximated —
  visible in its lower accuracy and higher refutation rate.
- Worlds are synthetic. They are drawn from real scientific topologies, but nothing here
  is evidence about real measurement noise or real experimental cost.
