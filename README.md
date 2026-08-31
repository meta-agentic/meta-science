# meta-science

**Hypothesis: a model can improve its own scientific method. Thesis: nothing counts
until it beats the champion, by a margin, on worlds it cannot see. We built that
gate — it refused Gemini twice.**

An agent does science on worlds it has never seen — forming hypotheses, designing its
own experiments, and being refuted by them. When it proposes a better method, the gate
decides. Never the agent.

The ideas behind it — Popper, the two axioms, and how the process ended up
disciplining its own authors: [Why a machine must be allowed to be
wrong](#why-a-machine-must-be-allowed-to-be-wrong), below.

Built on Gemini 3.5+ via the Google GenAI SDK, running on Cloud Run with a Firestore
ledger, declared in Terraform.

---

## The problem this is about

"Self-improving agent" is the most common unfalsifiable claim in the field. Its problem
is not that it is false; its problem is that, as usually stated, it *cannot* be false. A
system that *reports* it improved itself is indistinguishable from a system that logs `"improved!"`
and changes nothing. The demos always show successes, which proves nothing, because a
loop that can only succeed has no information in it. Karl Popper named this failure a
century ago: a theory that cannot be refuted by any conceivable event is not thereby
strong — it is thereby empty.

So we did not set out to build a self-improving agent. We set out to build the *gate*
such an agent would have to pass — and only then the agent. One invariant holds it up:

> **An agent never promotes its own output to canon — including its own improvements.**

The interesting artefact here is not a system that improves. It is a system that
**refuses to.**

---

## The axioms

Two refusals, stated up front — everything else descends from them.

**A1 — No agent is the judge of its own claims.**

> A ⊢ c  ⇏  ⊨ c

The two turnstiles of logic: `⊢` is *syntactic* — what an agent can derive; `⊨` is
*semantic* — what actually holds. The axiom says the first never purchases the second
when the prover judges itself: **derivation is not truth.** An agent has authority over
its own proofs, never over the world; the gate exists to bridge that gap from outside.
In practice the model proposes hypotheses, designs experiments, and suggests
improvements to its own method — but it never scores itself, never sees the held-out
worlds it will be judged on, and never writes to canon. Verdicts are computed, not
solicited. This is not distrust of any particular model; it is the constitutional
insight behind separated powers and referees who do not play: the roles of proposer and
judge corrupt each other when merged, whoever holds them.

Or, as a philosopher would have carved it:

> *Ex probatione propria non sequitur veritas.* — from one's own proving, truth does not follow.

**A2 — Seeing is not doing.**

> P(Y | do(X)) ≢ P(Y | X)

Pearl's distinction — conditioning is not intervening — is what makes discovery *cost*
something. Not `≠` but `≢` — *not identically equal*, and the distinction is the axiom's sharpest
edge: for an unconfounded X the two quantities **are** equal, which is exactly what a
randomised experiment buys. The operators differ; their values coincide only when it has
been earned. Our confounded worlds are built where they diverge — and observation alone
walks straight into the gap (0/4 recovered), while intervention walks around it (4/4).
Knowledge that can be had by looking is retrieval. Knowledge that must be paid for in
experiments is science.

The quantum objection to A2 — and where it leads — is taken up in [Why a machine must be
allowed to be wrong](#why-a-machine-must-be-allowed-to-be-wrong).

---

## What actually happens

One live run of `python3 run_evolution.py --generations 3`. The receipts are committed,
so this transcript can be checked rather than believed:

```
held-out worlds: 24  (never shown to the proposer)
champion champion-v1: +0.8704

gen 1  ✓ PROMOTED  gemini-1260
         diff   {'samples_per_arm': (200, 400)}
         champ +0.8704  challenger +0.8981
         beat the champion on held-out worlds by the required margin
         audit  FLAGGED (gemini-3.5-flash-lite): The score increase was driven by a significant drop in measurement cost that outweighed […]
         receipt b3e1652e80a0e2d9

gen 2  ✗ REFUSED   gemini-1740
         diff   {'samples_per_arm': (150, 200)}
         champ +0.8981  challenger +0.9120
         gained +0.0139, needed +0.02
         receipt ec154612250ff465

gen 3  ✗ REFUSED   gemini-2550
         diff   {'max_experiments': (8, 12)}
         champ +0.8981  challenger +0.8722
         gained -0.0259, needed +0.02
         receipt f723040336b97f9e

canon: gemini-1260
```

Three things are worth reading closely.

**The promotion was earned and still flagged.** Gemini found a real efficiency gain and it
cleared the margin — but a *second, different* model read the receipt and objected that the
gain was bought by letting accuracy fall from 0.9815 to 0.9537. The gate promotes on
evidence; the auditor may dissent in writing. Both are on the record.

**The refusals are the interesting part.** The second proposal genuinely scored *higher* and
was refused anyway, for gaining +0.0139 where the margin asks +0.02. Refusing a real gain is
what stops a system ratcheting itself forward on noise. The third scored worse outright. The
gate need not tell those two cases apart — neither clears the bar — but the receipts do.

**It stopped repeating itself.** After a second samples cut was refused, the proposer moved
to a different knob entirely — verdicts return to it as structured history, not prose.

Every verdict, promotion and refusal alike, writes a receipt carrying the diff, both
scores, the margin, the score decomposition and the held-out seeds — enough to re-derive
the decision independently.

**We ran it three times and published all three.** One promotion and two refusals in every
run. The proposer moved on to `max_experiments` by generation three in every run. Four of
the six refusals were of candidates that scored *higher* and missed the margin. The runs,
the receipts, and the one thing that did not reproduce — the auditor's verdict on an
identical promotion — are in [docs/receipts/](docs/receipts/).

---

## Two levels, one gate

**Level 1 — discovery.** The agent meets an unseen world, forms a hypothesis, designs an
intervention, and finds out it was wrong.

**Level 2 — self-evolution.** The agent proposes a change to *its own experiment-design
strategy*. Champion versus challenger on 24 held-out worlds it has never seen. The same
gate rules on both.

---

## Why a machine must be allowed to be wrong

*An essay on the ideas behind meta-science — and on the process that built it, which
turned out to be the same idea applied to ourselves.*

### The physicist's objection

A physicist will object to the second axiom, and did, in the person of this project's
author: quantum mechanics knows no passive spectator — observation *is* interaction. The
objection sharpened us twice.

First, the axiom's substance survives it: even in the quantum formalism, conditioning on
an outcome (post-selection) and preparing a state (intervention) remain different
operations; the slogan frays, the mathematics holds.

Second, pushed further, the objection revealed what a simulated benchmark is: the one
place where the observer genuinely stands outside the ontology — because we built the
ontology and enumerated its every edge. The side effects are real, and they live in the
host universe, not the guest one. Our determinism tests double as the experimental
proof: the same seed builds bit-identical worlds on a hot CPU or a cold one. And where
our own API leaks a miniature observer effect — unseeded observation advances the random
stream — we name the crack rather than polish it.

### What a refusal is worth

The agent's proposals land in a tier that is non-authoritative by construction.
Promotion to canon requires beating the incumbent on worlds the proposer cannot see or
enumerate, by a margin — because a gate without a margin ratchets on noise, which is how
a thousand tiny lucky wins launder randomness into "progress." Every verdict writes a
receipt sufficient to recompute it, and an independent auditor — a different model —
reads each promotion and may dissent, on the record, without veto.

In three live runs, all published, the gate promoted Gemini's first proposal and refused
its next two — every time. Most of those refusals were of *measured improvements*: real
gains, turned down for falling under the margin. Those refusals are worth more than any
promotion we could show you. A system that can only say yes to itself proves nothing by
saying yes.

### The process was the philosophy

The unexpected lesson: building this forced the same discipline onto us.

Our benchmark flattered us once — paired sampling made cutting measurement free, and the
"efficiency gains" our evolver kept finding were partly an artefact. We found it by
auditing our own results, measured both regimes, switched to the harder one, and
published the comparison. Our figures drifted from the code once — a process-randomised
hash quietly broke replayability — and the fix was to pin every published number to the
code by test. Our chart design was reviewed by an independent reasoner that rejected our
first axis for hiding real failure cases; it was right, and the correction is printed on
the figure. Even the second axiom was refined under fire from its own author. And the
collaboration that built all of it ran on the first axiom: an AI pair-engineer proposing
at speed, a human judging, refusing, and redirecting — neither of us trusted as the
judge of our own claims.

None of this was in the plan. All of it is the point. A method you only apply to your
subject is a pose; applied to yourself, it becomes a practice.

### Toward a thousand turns

Today the system runs a few gated turns of self-improvement, demonstrated end to end.
The architecture exists so that a thousand turns would still be falsifiable: margins
against noise, auditors against metric-gaming, receipts for lineage, and — the quiet
advantage of synthetic worlds — an inexhaustible supply of fresh, unseen tests, which
lets repetition remain science instead of becoming p-hacking.

Free for everyone, human or AI. That is not a licence footnote; it is the thesis
restated. Science is the practice of claims that anyone may check. We tried to build
software the same way.

*Ex probatione propria non sequitur veritas.* — including ours.

— *Marco Vanadia (mova), built meta-agentically with an AI pair-engineer, August 2026*

---

## Quickstart

```bash
git clone https://github.com/meta-agentic/meta-science && cd meta-science
python3 -m pip install -r requirements.txt
echo 'GEMINI_API_KEY=your-key' > .env          # https://aistudio.google.com/apikey
python3 -m pytest -q                           # no key needed: the full offline suite
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
| `GET /stats` | population figures over everything recorded |
| `GET /export.csv` | one row per hypothesis, joined to ground truth |

---

### Deploy

```bash
./scripts/verify.sh     # everything that must hold before deploying
cd infra
terraform init
terraform apply
```

Provisions Firestore, Cloud Run, a service account scoped to `roles/datastore.user`, and
the API key in Secret Manager. See [docs/architecture.md](docs/architecture.md).

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

### The measurement that settles it

Give Gemini the anonymised observations and forbid experiments, then ask for the causal
sign. Compare against the same agent allowed to intervene:

| | confounded worlds recovered |
|---|---|
| Gemini, observation only | **0 / 4** |
| The same loop, allowed to intervene | **4 / 4** |

Both readings are of identical worlds. The only difference is the ability to act. This is
also the adversarial test of anonymisation: if the surface leaked, the model would have
recognised the system and answered from memory instead of following the correlation into
the trap. It followed the correlation, every time.

Reproduce with `python3 -m pytest -m slow -q` (needs a key).

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
$ python3 -m pytest -q
all tests pass; 4 live-model tests deselected
```

Determinism is checked in a **subprocess**. An in-process check passed throughout
development while `hash()` — randomised per interpreter by `PYTHONHASHSEED` — was seeding
world generation, so the same seed silently built a different world in every run and no
receipt actually replayed. Only a fresh process catches that.

The four deselected tests make live model calls; run them with `python3 -m pytest -m slow`
and a key. They are excluded by default because each is several round trips to a
rate-limited endpoint, so including them makes a green run depend on quota rather than on
the code.

---

## We audited our own benchmark, and changed it

Late in the build we checked whether the two arms of an intervention share random draws.
They did — *common random numbers*, which makes the paired difference isolate the causal
effect. Elegant, and a trap: if the noise cancels, effect estimates stay precise however
few samples you draw, so **cutting measurement becomes free score.** That is very likely
why the proposer kept winning by asking for fewer samples.

So we measured it, on 24 held-out worlds:

| strategy | paired: accuracy · score | independent: accuracy · score |
|---|---|---|
| champion, 400 samples | 0.9815 · **+0.8704** | 0.9815 · **+0.8704** |
| frugal, 100 samples | 0.9815 · **+0.9537** | 0.9537 · **+0.9259** |
| very lean, 25 samples | 0.9815 · **+0.9745** | 0.8426 · **+0.8357** |

Read the accuracy columns. **Paired, accuracy does not move at all** — 0.9815 whether you
draw 400 samples or 25 — so the leanest strategy always wins and the metric has no
trade-off in it. Independent, accuracy degrades as measurement is cut, and the extreme
strategy correctly **loses** to the champion (+0.8357 against +0.8704).

**Independent noise is now the default**, and both demonstrated promotions survive it:
the offline demo's (100 samples per arm) at +0.9259 against +0.8704, and the live run's
(200 samples) at +0.8981 — gains of +0.0555 and +0.0277 against a required margin of
+0.02. Both facts are asserted by tests. The point is not that we got
it right first time — we did not. It is that the benchmark was checked against the
possibility that it was flattering us.

---

## A second model audits every promotion

Scoring higher is necessary and not sufficient. A challenger can score higher by
exploiting the metric rather than by doing better science — this project had a candidate
try exactly that, buying accuracy with more samples under a cost model that only charged
experiment count.

So each promotion is read by a **different Gemini model** (`gemini-3.5-flash-lite`, not
the `3.6-flash` that proposes) which argues about whether the win was earned. It sees the
score split into its parts, because the composite alone cannot separate *spent less and
kept the answers* from *spent less, lost accuracy, and the saving outran it*.

```
PROMOTED  gemini-1260   {'samples_per_arm': (200, 400)}
          champ +0.8704  challenger +0.8981
          audit FLAGGED (gemini-3.5-flash-lite): accuracy fell by 0.0278, which
                exceeds the noise threshold of 0.02
```

A live result, not a staged one: the gate promoted on the numbers and the auditor
disagreed on the record. Under paired arms this promotion looked free; under independent
noise it costs real accuracy, and the auditor says so.

It is **advisory and cannot veto.** It runs after the verdict and annotates the record —
a promotion that turned on a model's opinion would reintroduce exactly what the gate
exists to prevent. When the auditor is unreachable that is recorded as *absent*, never as
approval.

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

## Every run is recorded as evidence

The deployed service has an interactive page, but the more useful output is the data
behind it. Each run is stored with its seeds, full strategy and code commit — enough to
**recompute** the result, not merely read it.

```bash
python3 scripts/collect.py --worlds 48   # 384 runs, ~45s, offline, no API key
python3 scripts/analyse.py               # the tables
```

From that study — 2,560 hypotheses across 8 arms — three results:

- **Cutting measurement costs accuracy only under independent noise.** From 400 samples to
  25 costs 5.4 accuracy points and quadruples the variance; with paired arms it costs
  *nothing*, which is the artefact that once made this look like a free efficiency gain.
- **83.9%** of observational priors on the confounded template are inverted by the
  experiment that tests them.
- Edge recovery: **recall 1.000, precision 0.786** — the agent never misses a real causal
  edge and over-claims about one in five.

`GET /export.csv` gives one row per hypothesis joined to ground truth, long format,
straight into pandas or R. Full schema and findings in
[docs/dataset.md](docs/dataset.md). How worlds are generated, worded (two views, one
enforced boundary) and composed into compound problems: [docs/worlds.md](docs/worlds.md)
and the live inspector at `/world/{seed}/inspect`.

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
- A three-generation run is demonstrated, not an open-ended evolutionary run.
- The held-out set is 24 worlds. At 10, a single world flipping moves the mean by 0.10 —
  five times the promotion margin, which would make a "win" indistinguishable from noise.

---

## What's next — Level 3

The demonstrated system is Level 1 (discover effects in one world) and Level 2 (one
gated turn of self-evolution). The honest gap: each hypothesis gets one experiment and
one verdict, and the agent estimates *effects* — it never guesses the *law*. Science
runs on repetition, and repetition is the roadmap:

- **Replicated experiments — mechanism shipped, measured honestly.** `replications` is
  now a strategy knob the evolver can tune: each hypothesis re-runs across fresh seeds
  and the verdict is meta-analytic (mean effect + majority sign agreement), with
  replication charged in the cost, never free. R=1 reproduces the frozen history
  bit-for-bit, by test. The benchmark's answer so far: at equal total budget,
  replication is **cost-neutral in these worlds** (80×5 scores identically to 400×1) —
  exactly what statistics predicts under iid gaussian noise. Replication earns its keep
  against what these worlds do not yet contain: heavy-tailed noise, outlier seeds,
  drift. Building worlds mean enough for replication to *win* is the real next step.
- **Law recovery** — the model proposes structure, mechanism family and parameters,
  scored against held-out interventions. Today it recovers directions and magnitudes:
  causal discovery, not yet a law.
- **The Kepler test — real data, and a measurement of recall.** The obvious next dataset
  is the one that started modern astronomy: Tycho Brahe's Mars oppositions, the numbers
  Kepler ground through for years before the eight arc-minutes of residual that would
  not go away forced him to an ellipse. It is a harder test than it looks, in exactly
  this project's way. Mars is the most recognisable dataset in the history of science, so
  a model shown labelled longitudes answers "ellipse" from memory before it has fitted
  anything — retrieval, not discovery, which is why our generated worlds are anonymised
  at birth. And nobody intervenes on a planet: the data is purely observational, so the
  law must be earned by fitting rather than by acting. Both objections are the reason to
  run it — twice. Once labelled, once with the dates stripped, the units rescaled and the
  axes renamed; the gap between those two runs measures how much of a model's
  "discovery" is recall, on the one dataset where memorisation is guaranteed.
- **Open-ended repeated self-evolution** — many generations, not one turn. The gate is
  what makes that safe rather than reckless: the margin stops ratcheting on noise, the
  auditor catches metric-gaming, receipts keep the lineage replayable, and ever-fresh
  generated held-out worlds are the pre-registration analogue that keeps a thousand
  repetitions from becoming p-hacking.

---

## Licence

**GPL-3.0-or-later** — copyleft, as science should be: free for everyone, human or AI.
Use it, study it, improve it; keep it free for the next reader.
