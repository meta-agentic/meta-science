# Three live runs, committed

A transcript in a README is a story. These are the receipts.

Three consecutive live runs of `python3 run_evolution.py --generations 3`, recorded in
one sitting on 2026-08-30. **All three are here. None were discarded**, and no run was
re-rolled to get a better-looking one — which is the only reason the numbers below mean
anything.

Each run starts from the same champion (`champion-v1`, +0.8704) and the same opening
note. Gemini proposes; the gate decides on 24 held-out worlds the proposer never sees.
Every verdict writes a receipt carrying the diff, both scores, the margin, the score
decomposition, the held-out seeds and the auditor's opinion — enough to recompute the
decision without trusting this file.

## What happened

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| **gen 1** | ✓ `gemini-1740` samples 400→150<br>+0.8704 → +0.9120 (**+0.0416**) | ✓ `gemini-1260` samples 400→200<br>+0.8704 → +0.8981 (**+0.0277**) | ✓ `gemini-1740` samples 400→150<br>+0.8704 → +0.9120 (**+0.0416**) |
| **gen 2** | ✗ `gemini-5808` samples 150→120<br>gained +0.0084 | ✗ `gemini-1740` samples 200→150<br>gained +0.0139 | ✗ `gemini-6396` samples 150→100<br>gained +0.0139 |
| **gen 3** | ✗ `gemini-2550` experiments 12→8<br>gained **−0.0287** | ✗ `gemini-2550` experiments 12→8<br>gained **−0.0259** | ✗ `gemini-7660` experiments 12→10<br>gained +0.0042 |
| **audit on the promotion** | FLAGGED | FLAGGED | legitimate |
| **canon** | `gemini-1740` | `gemini-1260` | `gemini-1740` |

## What reproduces

**One promotion, two refusals — 3 out of 3.** The shape of the result is not a lucky
draw. Every run bought the large first cut in measurement and refused everything after
it.

**The proposer changes the subject — 3 out of 3.** After two sample-size proposals are
answered (one promoted, one refused), it moves to a different knob entirely,
`max_experiments`, in every run. Verdicts return to it as structured history, so it
does not re-propose what was just refused.

**Both refusal modes appear.** Four refusals were of candidates that genuinely scored
*higher* (+0.0042 to +0.0139) and were refused for gaining less than the margin — these
are the interesting ones, because refusing a real gain is what stops a system ratcheting
itself forward on noise. Two were of candidates that scored *worse*, in both cases the
same proposal: cutting the experiment budget from 12 to 8.

## What does not reproduce — and we are not hiding it

Runs 1 and 3 contain the **identical promotion** — same candidate, same diff, same
scores — and the auditor flagged it in run 1 but called it legitimate in run 3. The
auditor is a language model reading a receipt; it is advisory, it has no veto, and it
is not deterministic. That is a real limitation, and it is the reason the auditor was
built to annotate the record rather than to control it. A gate whose verdicts depended
on this would inherit the variance; ours does not — the promotion is decided by the
margin either way, and the disagreement is preserved on both receipts.

The gate itself is deterministic: the same strategy on the same seeds always produces
the same score. What varies between runs is only what Gemini *proposes*.

## Replay one

```bash
python3 - <<'EOF'
import json, sys
sys.path.insert(0, "src")
from metascience.evolution import evaluate_strategy, held_out_seeds
from metascience.strategy import Strategy

r = json.load(open("docs/receipts/run-2/1788114410451-gemini-1260-PROMOTED.json"))
seeds = r["world_seeds"]
champ = evaluate_strategy(Strategy(), seeds)
chal = evaluate_strategy(Strategy(**{k: v[0] for k, v in r["diff"].items()}), seeds)
print(f"receipt says  champ {r['champion_score']:+.4f}  challenger {r['challenger_score']:+.4f}")
print(f"recomputed    champ {champ:+.4f}  challenger {chal:+.4f}")
print("verdict holds:", (chal >= champ + r["margin_required"]) == (r["verdict"] == "PROMOTED"))
EOF
```

No API key is needed to check any of this. Scoring is offline and deterministic; only
the proposing was live.

`tests/test_committed_receipts.py` does this for all nine receipts on every test run: it
walks each run forward, rebuilds the champion from the promotions, recomputes both
scores, and asserts the verdict follows from the margin — then checks that the README's
transcript quotes receipts that actually exist here. The transcript cannot drift from
the evidence again without the suite saying so.

## Which run the README shows

The main README transcribes **run 2**, because it is the run that reproduces the demo
video's transcript, and the two artefacts should agree. That choice is about
consistency, not flattery: run 2 is not the most favourable of the three — its third
generation is an outright regression, whereas run 3 ends with the more impressive kind
of refusal, a real gain turned down for being under the margin. All three are here
either way.
