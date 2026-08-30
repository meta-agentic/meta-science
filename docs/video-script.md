# Demo video — the shipped cut

The video is assembled from reusable clips — an intro, a corpus, an outro — each
rendered by [`video/build.py`](../video/build.py) and narrated by Gemini TTS (voice:
Kore) via [`video/narrate.py`](../video/narrate.py). The narration is written to
complement the slides, not read them aloud. Final renders live in `video/final/`
(tracked with Git LFS), subtitles in `final.srt`.

The narrator's script, clip by clip:

## Intro — the problem

> What would it take to trust a machine that says it made itself better? Not a bigger claim — a smaller one, that can be checked.

## The axioms

> Every science begins with what it refuses to assume. No agent judges its own claims — derivation is not truth. Seeing is not doing — the two coincide only when confounding is absent, which is exactly what may never be assumed. And improvement only counts when it is proven, on worlds the prover cannot see. The rest is engineering.

## A world the agent has never seen

> Start by taking everything away. No names, no context, no textbook to remember. What is left is the only thing that cannot be faked: the ability to find out.

## The trap — seeing is not doing

> Data can be perfectly clear, and perfectly wrong. The only way past a hidden cause is to reach into the world and move something. Reading alone fails every time. Acting succeeds every time.

## Refutations, both directions

> Real science cuts both ways. Some guesses survive their experiment, some die by it — and the machine finds out which, the hard way. It wrote its predictions down first, so there is no taking them back.

## The ghost in the shell — gated self-evolution

> And here is the ghost in the shell — the model thinking about its own method, in its own words. Its idea was good, so it passed. Its next two ideas were also good. Not good enough. That is the whole point.

## The evidence base

> None of this rests on a lucky run. Hundreds of worlds, thousands of tests — and any of them can be re-run by anyone, from a single seed.

## The statistics — and the rigged benchmark

> Spend a quarter of the budget: same answers. Spend even less, and the spread gives you away — unless the benchmark is rigged to hide it. Ours was, once. We found it, fixed it, and published both.

## Replication — the system answers the oldest question

> In the end we asked the system the oldest question in science: do you need repetition? It gave the statistician's answer — not here, not yet — and told us exactly what kind of world would change its mind.

## Outro — one more thing

> One gated turn today. A thousand tomorrow — and every one of them would still have to show a receipt. ... One more thing. The voice you have been listening to... is Gemini. The system just narrated its own demo. Meta-science. Free for everyone — human, or A.I.

---

The reveal at the end is literal: the narration audio is synthesized by Gemini, so
the system's own model voices the demo of the gate that refused it.
