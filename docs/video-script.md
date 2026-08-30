# Demo video — script and storyboard

**Target: 4:00.** The rubric asks for the problem, the value proposition, and live
functionality. Two beats carry the entry: the experiment that kills the agent's own
hypothesis, and the benchmark that refuses the agent's own improvement. Everything else
is setup for those.

Record `python3 demo.py` full-screen. It is offline and deterministic, so takes are
repeatable. Use `--live` only if you want the Gemini call visible on camera.

---

## 0:00 – 0:25 · The problem

> "Every self-improving agent demo shows you a system getting better. None of them show
> you the system being told it didn't. And that's the only part that would prove
> anything — because a system that *reports* it improved is indistinguishable from one
> that logs 'improved' and changes nothing."

**On screen:** title card, then the terminal.

---

## 0:25 – 1:00 · What the agent is allowed to know

Run the demo. Stop on beat [1].

> "This is everything the agent gets. Variables called X1 and X2. No names, no units, no
> documentation. Two things it can do: look at the system, or reach in and change it.
>
> The names are stripped deliberately. If I called these 'pressure' and 'volume', Gemini
> would recognise the system and recite the law from memory — and then design experiments
> that confirm what it had already decided. That's not discovery, it's recall."

---

## 1:00 – 1:35 · The trap

Beat [2] — the correlation.

> "So the agent looks. And the data is unambiguous — a correlation near minus one.
> Strong, clean, and completely wrong. There's a hidden common cause driving both
> variables, and it's swamping the real relationship.
>
> Any system that reasons from data alone stops here — with the sign backwards."

**On screen:** hold on the red correlation.

---

## 1:35 – 2:15 · The refutation

Beat [3].

> "Now it acts. It commits a prediction first — negative, following the correlation —
> and *then* runs the experiment.
>
> Measured effect: strongly positive. The opposite sign. Its own experiment just killed
> its own hypothesis.
>
> That order matters. The prediction is written down before the experiment runs, and the
> verdict comes from comparing the two. The model is never asked whether it was right."

**On screen:** the red `REFUTED`.

---

## 2:15 – 3:00 · The measurement that settles it

**On screen:** the comparison table.

> "We ran that as a controlled test. Give Gemini the observations and forbid experiments:
> it recovers the causal direction in zero out of four confounded worlds. Give the same
> loop the ability to intervene: four out of four.
>
> Identical worlds. The only difference is the ability to act."

---

## 3:00 – 3:40 · The system improves itself — and is refused

Beats [4] and [5].

> "Now one level up. The agent proposes a change to its own experiment-design strategy.
> Gemini proposes; it never sees the twenty-four held-out worlds, never runs the scorer,
> and gets no say in the verdict.
>
> First proposal: same conclusions on a quarter of the measurement. Genuinely better.
> Promoted.
>
> Second: refused. And notice *why* — not because it was stupid, but because it didn't
> clear the margin. Canon didn't move. Both decisions wrote a receipt you can replay."

**On screen:** hold on `REFUSED`, then `canon holds: frugal-v2`.

---

## 3:40 – 4:00 · Close

> "Built on Gemini 3.6 through the GenAI SDK, Firestore for the ledger, Cloud Run,
> declared in Terraform.
>
> It isn't the first AI scientist and doesn't claim to be. What it is, is a
> self-improving system that can be checked — because it can refuse itself."

---

## A note on the numbers

**Read them off the screen, don't recite them from here.** Exact values move whenever the
world generator changes — they already did once, when a hashing fix altered the
constants. The *shapes* are stable and are what the narration should commit to: the
correlation is strongly negative, the measured effect is strongly positive and of
comparable magnitude, and the observation-only baseline is 0/4 against 4/4.

At the time of writing, seed 7 gives `corr(X2, X1) = −0.961` and a measured effect of
`+1.183`. Re-run `python3 demo.py` before recording and use whatever it prints.

## Notes

- **Do not oversell.** The prior-art disclaimer at the end costs eight seconds and buys
  credibility with any judge who knows the literature.
- **Let the refusals sit.** Two full seconds on each red verdict. They are the entry.
- **Show the terminal, not slides.** The rubric asks for live functionality, and the
  output is legible enough to read on screen.
- If the mask-reveal is wanted, add after 2:15: *"That world was a confounded treatment
  effect in disguise. The agent never saw a single domain word."*
