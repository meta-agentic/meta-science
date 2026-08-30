# meta-science

**An agent that does science on worlds it has never seen — forming hypotheses, designing
its own experiments, and being refuted by them — and that improves its own scientific
method only when a frozen benchmark proves the improvement real.**

Built on Gemini 3.5+ via the Google GenAI SDK, running on Cloud Run with a Firestore
ledger, declared in Terraform.

---

## The problem this is about

"Self-improving agent" is the most common unfalsifiable claim in the field. A system that
*reports* it improved itself is indistinguishable from a system that logs `"improved!"`
and changes nothing. The demos always show successes, which proves nothing, because a
loop that can only succeed has no information in it.

So this project is built around one invariant:

> **An agent never promotes its own output to canon — including its own improvements.**

The interesting artefact here is not a system that improves. It is a system that
**refuses to.**

---

## What actually happens

A representative run of `python3 run_evolution.py --generations 3`:

```
held-out worlds: 24  (never shown to the proposer)
champion champion-v1: +0.8704

gen 1  ✓ PROMOTED  gemini-9112
         diff   {'samples_per_arm': (150, 400)}
         champ +0.8704  challenger +0.9398
         beat the champion on held-out worlds by the required margin

gen 2  ✗ REFUSED   gemini-4886
         diff   {'samples_per_arm': (120, 150)}
         champ +0.9398  challenger +0.9482
         gained +0.0083, needed +0.02

gen 3  ✗ REFUSED   gemini-5269
         diff   {'samples_per_arm': (100, 150)}
         gained +0.0139, needed +0.02
```

Gemini found a real improvement — the same conclusions on a fraction of the measurement —
and it was promoted. Then it proposed two further refinements that *did* score higher,
and both were **refused for gaining less than the margin.** Refusing marginal gains is
the point: it is what stops a system ratcheting itself forward on noise.

Every verdict, promotion and refusal alike, writes a receipt carrying the diff, both
scores, the margin, and the held-out seeds — enough to re-derive the decision
independently.

---

## Two levels, one gate

**Level 1 — discovery.** The agent meets an unseen world, forms a hypothesis, designs an
intervention, and finds out it was wrong.

**Level 2 — self-evolution.** The agent proposes a change to *its own experiment-design
strategy*. Champion versus challenger on 24 held-out worlds it has never seen. The same
gate rules on both.

---

## Why the refutations are real

The prediction is committed to the trace **before** the experiment runs, and the verdict
is computed by comparing prediction to result. The model is never asked whether it was
right. A hypothesis recorded after the result is not a hypothesis; it is a description.

The worlds make this bite. One template is required to **invert**: its observational
correlation carries the opposite sign to its true causal effect.

| seed | observational corr | true causal effect |
|---|---|---|
| 0 | **−0.918** | **+1.466** |
| 7 | −0.834 | +1.353 |
| 13 | −0.960 | +1.155 |

An agent that only looks at data concludes the opposite of the truth. Only intervention
recovers it — which is the entire argument for autonomy, made unfakeable.

---

## Anonymisation is a test, not a promise

World templates are seeded from real scientific topologies, because real science supplies
non-trivial structure and known ground truth for free. But every retrievable surface is
stripped at birth — domain names become `X₁…Xₙ`, labels are shuffled per world, constants
and exponents are randomised, the functional family varies.

Without this the agent **retrieves** instead of discovering: Gemini already knows the gas
laws, would emit one on recognising the shape, then design experiments confirming what it
had already said. The benchmark would measure recall, and every number above would be
meaningless.

So it is enforced by tests — a 41-term banned lexicon asserted against everything the
agent can see, on every template, on every seed, plus checks that constants vary and that
no role is pinned to a label.

```
$ python3 -m pytest tests/ -q
7 passed
```

---

## Results per template

Six topologies, deterministic reasoner, scored on held-out interventions:

| template | shape | hypotheses refuted | direction accuracy |
|---|---|---|---|
| T1 | multiplicative state relation | 9/12 | 0.89 |
| T2 | exponential response | 4/6 | 1.00 |
| T3 | linear transport chain | 7/12 | 1.00 |
| T4 | saturating compartment flow | 3/6 | 1.00 |
| T5 | hidden common cause | 2/2 | 1.00 |
| T6 | **sign inversion under confounding** | 2/2 | 1.00 |

T1 is 0.89 rather than 1.00 because it is genuinely multiplicative and a linear effect
estimate is an approximation there. That number is reported rather than tuned away.

---

## Quickstart

```bash
git clone https://github.com/meta-agentic/meta-science && cd meta-science
python3 -m pip install -r requirements.txt
echo 'GEMINI_API_KEY=your-key' > .env          # https://aistudio.google.com/apikey
python3 -m pytest tests/ -q                    # no key needed: anonymisation suite
python3 run_evolution.py --offline             # no key needed: gate, both directions
python3 run_evolution.py --generations 3       # live: Gemini proposes, gate decides
```

The `--offline` path runs the whole gate with a scripted proposer, so **the governance
claim can be verified without an API key at all.**

Serve it locally:

```bash
uvicorn app:app --reload --port 8080
```

| route | what it shows |
|---|---|
| `GET /world/7` | everything the agent is allowed to know |
| `GET /discover/7` | a run, including which hypotheses its experiments killed |
| `POST /evolve` | one generation: Gemini proposes, the gate decides |
| `GET /receipts` | every verdict, promotions and refusals alike |

---

## Deploy

```bash
cd infra
terraform init
terraform apply
```

Provisions Firestore, Cloud Run, a service account scoped to `roles/datastore.user`, and
the API key in Secret Manager. See [docs/architecture.md](docs/architecture.md).

---

## The stack

| Requirement | How it is met |
|---|---|
| **Gemini 3.5 or newer** | `gemini-3.6-flash`, falling back to `gemini-3.5-flash` |
| **Google agent framework** | **GenAI SDK** (`google-genai`) drives both reasoning roles |
| **Google Cloud service** | **Firestore** holds the ledger; **Cloud Run** executes runs |

`gemini-3.7-flash` returned `503 UNAVAILABLE` under load during development, so the
cascade starts at 3.6. A benchmark that dies because one model is busy is not a
benchmark. Every entry in the cascade is ≥ 3.5.

---

## What is not claimed

Automated scientific discovery has substantial prior art — active learning, causal
discovery, rule-induction benchmarks in the Zendo/Eleusis tradition. **This is not the
first AI scientist and does not claim to be.**

What is offered is narrower and, we think, more useful: **falsifiable self-improvement**.
A loop whose every promotion is earned against evidence the proposer cannot see, cannot
score, and cannot tune against — and which leaves a receipt either way.

Known limits, stated rather than buried:

- Effect estimation is linear, so genuinely multiplicative worlds (T1) are approximated.
- One generation is demonstrated end-to-end, not an open-ended evolutionary run.
- The held-out set is 24 worlds. At 10, a single world flipping moves the mean by 0.10 —
  five times the promotion margin, which would make a "win" indistinguishable from noise.

---

## Licence

MIT.
