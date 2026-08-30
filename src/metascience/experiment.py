"""Experiment records — the unit of evidence.

Written so that a record is enough to *recompute* its own result later. That is a higher
bar than logging what happened, and it is the bar a paper needs: a reader with the record
and the code at the stated commit must be able to reproduce the number, not merely read it.

So each record carries the seeds, the full strategy, the code version, the model names,
and the world's hidden ground truth. Ground truth is recorded **after the fact, for
analysis only** — nothing in the agent's path ever reads it, and it lives in a separate
field so that boundary stays visible rather than remembered.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = 1


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=5)
        # -uno: untracked files do not make the code dirty. The frozen study artifact
        # is itself untracked at generation time, so counting it would make every
        # freshly generated artifact stamp itself "-dirty" — a chicken-and-egg flag
        # that says nothing about the code that produced the numbers.
        dirty = subprocess.run(["git", "status", "--porcelain", "-uno"],
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return out.stdout.strip()[:12] + ("-dirty" if dirty else "")
    except Exception:  # noqa: BLE001 — provenance is best-effort, never fatal
        return "unknown"


def provenance(models: dict[str, str] | None = None) -> dict:
    """Everything needed to say which code and which models produced a number."""
    return {
        "schema_version": SCHEMA_VERSION,
        "git_commit": _git_commit(),
        "image": os.environ.get("K_REVISION", "local"),
        "python": platform.python_version(),
        "models": models or {},
        "recorded_at": time.time(),
    }


@dataclass
class Trial:
    """One agent-versus-one-world encounter."""
    world_seed: int
    template_id: str
    variables: list[str]
    experiments: list[dict]          # hypothesis, intervention, measured effect, verdict
    model: dict[str, float]          # what the agent concluded
    held_out: dict                   # scored on interventions it never saw
    refutations: int
    # Analysis-only. Never read on the agent's path; kept apart so that stays checkable.
    ground_truth: dict | None = None


@dataclass
class ExperimentRecord:
    """One run. Discovery, or one generation of self-evolution."""
    run_id: str
    kind: str                        # "discovery" | "evolution"
    created_at: float
    provenance: dict
    config: dict                     # strategy, margin, world count — the full setting
    seeds: list[int]
    trials: list[Trial] = field(default_factory=list)
    outcome: dict | None = None      # evolution: verdict, scores with parts, diff, audit
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["digest"] = self.digest()
        return d

    def digest(self) -> str:
        """Content hash over the inputs, so an identical setting is recognisable."""
        body = json.dumps({"kind": self.kind, "config": self.config, "seeds": self.seeds,
                           "commit": self.provenance.get("git_commit")}, sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()[:16]

    @staticmethod
    def new_id(kind: str, seeds: list[int], config: dict, clock: float) -> str:
        stamp = int(clock * 1000)
        tag = hashlib.sha256(
            json.dumps({"s": seeds, "c": config}, sort_keys=True).encode()).hexdigest()[:6]
        return f"{kind}-{stamp}-{tag}"


def trial_from_run(world, run, held_out: dict) -> Trial:
    """Build a Trial from a discovery run, attaching ground truth for later analysis."""
    return Trial(
        world_seed=world.seed,
        template_id=world.template_id,
        variables=list(world.observable),
        experiments=[{
            "cause": e.hypothesis.cause,
            "effect": e.hypothesis.effect,
            "predicted_sign": e.hypothesis.predicted_sign,
            "basis": e.hypothesis.basis,
            "lo": e.lo, "hi": e.hi, "n": e.n,
            "measured_effect": e.observed_effect,
            "verdict": e.verdict,
        } for e in run.experiments],
        model=run.model,
        held_out=held_out,
        refutations=len(run.refutations),
        ground_truth=world.ground_truth(),
    )


# -- aggregation over records ------------------------------------------------

def summarise(records: list[dict]) -> dict:
    """Population-level figures — the table a paper opens with.

    Kept as plain arithmetic over stored records rather than recomputed from the code,
    so the summary describes what was actually observed and not what the current code
    would produce today.
    """
    discovery = [r for r in records if r.get("kind") == "discovery"]
    evolution = [r for r in records if r.get("kind") == "evolution"]

    trials = [t for r in discovery for t in r.get("trials", [])]
    by_template: dict[str, list[float]] = {}
    refutations = hypotheses = 0
    for t in trials:
        acc = (t.get("held_out") or {}).get("direction_accuracy")
        if acc is not None:
            by_template.setdefault(t.get("template_id", "?"), []).append(acc)
        refutations += t.get("refutations", 0)
        hypotheses += len(t.get("experiments", []))

    verdicts = [(r.get("outcome") or {}).get("verdict") for r in evolution]
    promoted = verdicts.count("PROMOTED")
    refused = verdicts.count("REFUSED")
    audits = [(r.get("outcome") or {}).get("audit") or {} for r in evolution]
    flagged = sum(1 for a in audits if a.get("legitimate") is False)

    return {
        "records": len(records),
        "discovery_runs": len(discovery),
        "evolution_generations": len(evolution),
        "trials": len(trials),
        "hypotheses_tested": hypotheses,
        "hypotheses_refuted": refutations,
        "refutation_rate": round(refutations / hypotheses, 4) if hypotheses else None,
        "direction_accuracy_by_template": {
            k: {"mean": round(sum(v) / len(v), 4), "n": len(v)}
            for k, v in sorted(by_template.items())
        },
        "promotions": promoted,
        "refusals": refused,
        "promotion_rate": round(promoted / len(verdicts), 4) if verdicts else None,
        "promotions_flagged_by_auditor": flagged,
    }


def to_csv_rows(records: list[dict]) -> list[dict]:
    """One row per hypothesis tested — the long format analysis actually wants."""
    rows = []
    for r in records:
        for t in r.get("trials", []):
            for e in t.get("experiments", []):
                truth = (t.get("ground_truth") or {}).get("edges", {})
                is_real = e["cause"] in truth.get(e["effect"], [])
                rows.append({
                    "run_id": r.get("run_id"),
                    "git_commit": (r.get("provenance") or {}).get("git_commit"),
                    "world_seed": t.get("world_seed"),
                    "template_id": t.get("template_id"),
                    "strategy": (r.get("config") or {}).get("strategy", {}).get("name"),
                    "samples_per_arm": (r.get("config") or {}).get("strategy", {}).get("samples_per_arm"),
                    "paired_arms": (r.get("config") or {}).get("strategy", {}).get("paired_arms"),
                    "cause": e["cause"],
                    "effect": e["effect"],
                    "predicted_sign": e["predicted_sign"],
                    "measured_effect": e["measured_effect"],
                    "verdict": e["verdict"],
                    "edge_exists_in_ground_truth": is_real,
                    "direction_accuracy": (t.get("held_out") or {}).get("direction_accuracy"),
                })
    return rows


# -- recording ---------------------------------------------------------------

def record_discovery(ledger, world, run, held_out: dict, strategy,
                     models: dict[str, str], notes: str = "") -> ExperimentRecord:
    """Persist one agent-versus-one-world encounter."""
    from dataclasses import asdict as _asdict

    now = time.time()
    config = {"strategy": _asdict(strategy)}
    rec = ExperimentRecord(
        run_id=ExperimentRecord.new_id("discovery", [world.seed], config, now),
        kind="discovery",
        created_at=now,
        provenance=provenance(models),
        config=config,
        seeds=[world.seed],
        trials=[trial_from_run(world, run, held_out)],
        notes=notes,
    )
    ledger.put_experiment(rec.to_dict())
    return rec


def record_generation(ledger, receipt, champion, challenger, seeds: list[int],
                      models: dict[str, str], notes: str = "") -> ExperimentRecord:
    """Persist one turn of the wheel, with both arms' scores kept apart.

    The receipt already proves the verdict. This adds the surrounding setting — seeds,
    both full strategies, code version — so the verdict can be *recomputed*, which is
    what a reader checking the claim will want to do.
    """
    from dataclasses import asdict as _asdict

    now = time.time()
    config = {"strategy": _asdict(champion), "challenger": _asdict(challenger),
              "margin": receipt.margin_required, "n_worlds": len(seeds)}
    rec = ExperimentRecord(
        run_id=ExperimentRecord.new_id("evolution", seeds, config, now),
        kind="evolution",
        created_at=now,
        provenance=provenance(models),
        config=config,
        seeds=list(seeds),
        outcome={
            "verdict": receipt.verdict,
            "candidate": receipt.candidate,
            "parent": receipt.parent,
            "diff": receipt.diff,
            "champion_score": receipt.champion_score,
            "challenger_score": receipt.challenger_score,
            "champion_parts": receipt.champion_parts,
            "challenger_parts": receipt.challenger_parts,
            "margin_required": receipt.margin_required,
            "reason": receipt.reason,
            "audit": receipt.audit,
            "receipt_digest": receipt.digest(),
        },
        notes=notes,
    )
    ledger.put_experiment(rec.to_dict())
    return rec
