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

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env, model_name  # noqa: E402
from metascience.discovery import run_discovery, score_on_held_out  # noqa: E402
from metascience.auditor import audit_promotion  # noqa: E402
from metascience.evolution import (evaluate_detailed, evaluate_strategy,  # noqa: E402
                                   held_out_seeds, run_generation)
from metascience.experiment import (record_discovery, record_generation,  # noqa: E402
                                    summarise, to_csv_rows)
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
    """The interactive surface. Self-contained: no CDN, no external fetches."""
    page = Path(__file__).parent / "static" / "index.html"
    return page.read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    """Not /healthz: Google's frontend intercepts that path and returns its own 404."""
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
    held_out = score_on_held_out(w, run, probes, seed=seed + 5000)
    rec = record_discovery(_ledger(), w, run, held_out, Strategy(),
                           models={"reasoner": model_name() if live else "heuristic"})
    return {
        **run.to_dict(),
        "held_out_score": held_out,
        "reasoner": "gemini" if live else "heuristic",
        "run_id": rec.run_id,
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
    challenger_holder = {}
    proposer = GeminiProposer()
    original = proposer.propose

    def capture(champ, notes=""):
        challenger_holder["c"] = original(champ, notes)
        return challenger_holder["c"]

    proposer.propose = capture
    _, receipt = run_generation(
        ledger, gate, champion, proposer, seeds,
        "accuracy is saturated on most worlds; 12 experiments x 400 samples each")
    rec = record_generation(ledger, receipt, champion, challenger_holder["c"], seeds,
                            models={"proposer": model_name(),
                                    "auditor": "gemini-3.5-flash-lite"})
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
        "run_id": rec.run_id,
    }


@app.get("/receipts")
def receipts() -> dict:
    led = _ledger()
    rows = led.receipts() if hasattr(led, "receipts") else []
    return {"count": len(rows), "receipts": rows[-20:]}


# -- the evidence base -------------------------------------------------------

@app.get("/experiments")
def experiments(limit: int = Query(100, le=500)) -> dict:
    """Every recorded run, newest last. Each one carries what it needs to be rerun."""
    rows = _ledger().experiments(limit=limit)
    return {"count": len(rows), "experiments": rows}


@app.get("/stats")
def stats() -> dict:
    """Population-level figures over everything recorded — the table a paper opens with.

    Computed from stored records rather than by rerunning the code, so it describes what
    was actually observed and not what the current version would produce today.
    """
    return summarise(_ledger().experiments(limit=500))


@app.get("/export.csv", response_class=PlainTextResponse)
def export_csv() -> str:
    """One row per hypothesis tested, joined to ground truth — the long format analysis
    actually wants. Straight into pandas or R without reshaping."""
    import csv
    import io

    rows = to_csv_rows(_ledger().experiments(limit=500))
    if not rows:
        return "no experiments recorded yet\n"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
