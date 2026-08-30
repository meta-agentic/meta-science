"""HTTP surface for the demo.

Deliberately thin. The interesting behaviour lives in the library; this exposes three
views of it so a judge can watch the system work without a checkout:

  /world/{seed}   what the agent sees — opaque labels and nothing else
  /discover/{seed} a discovery run, including which hypotheses were refuted
  /evolve         one turn of the wheel: Gemini proposes, the gate decides
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env, model_name  # noqa: E402
from metascience.discovery import run_discovery, score_on_held_out  # noqa: E402
from metascience.auditor import audit_promotion  # noqa: E402
from metascience.evolution import (evaluate_detailed, evaluate_strategy,  # noqa: E402
                                   held_out_seeds, run_generation)
from metascience.gemini import TUNABLE, GeminiProposer, GeminiReasoner  # noqa: E402
from metascience.ledger import FileLedger, PromotionGate  # noqa: E402
from metascience.reasoner import HeuristicReasoner  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402
from metascience.templates import generate  # noqa: E402

load_env()
app = FastAPI(title="meta-science", description="An agent that does science, and can be refuted.")


def _ledger():
    """Firestore in the cloud, filesystem locally — the gate cannot tell the difference."""
    if os.environ.get("K_SERVICE"):          # set by Cloud Run
        from metascience.firestore_ledger import FirestoreLedger
        return FirestoreLedger(project=os.environ.get("GEMINI_PROJECT"))
    return FileLedger("runs")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><meta charset=utf-8>
<title>meta-science</title>
<style>body{font:16px/1.6 system-ui;max-width:46rem;margin:3rem auto;padding:0 1rem}
code{background:#f4f4f5;padding:.1rem .35rem;border-radius:3px}</style>
<h1>meta-science</h1>
<p>An agent that does science on worlds it has never seen &mdash; forming hypotheses,
designing its own experiments, and being refuted by them &mdash; and that improves its
own method only when a frozen benchmark proves the improvement real.</p>
<ul>
<li><code>GET /world/7</code> &mdash; everything the agent is allowed to know</li>
<li><code>GET /discover/7</code> &mdash; a run, with the hypotheses its experiments killed</li>
<li><code>POST /evolve</code> &mdash; one generation: Gemini proposes, the gate decides</li>
<li><code>GET /receipts</code> &mdash; every verdict, promotions and refusals alike</li>
</ul>"""


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "model": model_name()}


@app.get("/world/{seed}")
def world(seed: int) -> dict:
    """The agent's entire view. No structure, no domain terms, no ground truth."""
    return generate(seed).describe()


@app.get("/discover/{seed}")
def discover(seed: int, live: bool = False) -> dict:
    w = generate(seed)
    reasoner = GeminiReasoner() if live else HeuristicReasoner()
    run = run_discovery(w, reasoner, Strategy(), seed=seed)
    variables = list(w.observable)
    probes = [(variables[0], 0.5), (variables[0], -0.5)]
    return {
        **run.to_dict(),
        "held_out_score": score_on_held_out(w, run, probes, seed=seed + 5000),
        "reasoner": "gemini" if live else "heuristic",
    }


@app.post("/evolve")
def evolve() -> dict:
    """Gemini proposes a change to the scientist's own method; the gate rules on it."""
    seeds = held_out_seeds(24)
    ledger = _ledger()
    gate = PromotionGate(
        ledger, evaluate_strategy, margin=0.02, detailed=evaluate_detailed,
        auditor=lambda r: audit_promotion(r, {k: t.__name__ for k, t in TUNABLE.items()}))
    champion = Strategy()
    _, receipt = run_generation(
        ledger, gate, champion, GeminiProposer(), seeds,
        "accuracy is saturated on most worlds; 12 experiments x 400 samples each")
    return {
        "verdict": receipt.verdict,
        "candidate": receipt.candidate,
        "diff": receipt.diff,
        "champion_score": receipt.champion_score,
        "challenger_score": receipt.challenger_score,
        "margin_required": receipt.margin_required,
        "reason": receipt.reason,
        "digest": receipt.digest(),
        "held_out_worlds": len(seeds),
        "score_parts": {"champion": receipt.champion_parts,
                        "challenger": receipt.challenger_parts},
        "audit": receipt.audit,
    }


@app.get("/receipts")
def receipts() -> dict:
    led = _ledger()
    rows = led.receipts() if hasattr(led, "receipts") else []
    return {"count": len(rows), "receipts": rows[-20:]}
