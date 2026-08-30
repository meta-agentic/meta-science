"""Level 1 — the discovery loop.

The agent forms a falsifiable prediction, *then* runs the experiment that can kill it.
Order matters: a hypothesis recorded after the result is not a hypothesis, it is a
description. So the prediction is committed to the trace before `intervene` is called,
and the verdict is computed by comparing the two — never by asking the reasoner whether
it was right.

The reasoner only *ranks* what to test. Conclusions come from interventions alone, which
is why an agent that merely observes gets the confounded worlds backwards.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .reasoner import Reasoner
from .strategy import Strategy
from .worlds import World

SUPPORTED, REFUTED = "SUPPORTED", "REFUTED"


@dataclass
class Hypothesis:
    cause: str
    effect: str
    predicted_sign: int          # committed BEFORE the experiment
    basis: str                   # what the prediction was drawn from


@dataclass
class Experiment:
    hypothesis: Hypothesis
    lo: float
    hi: float
    n: int
    observed_effect: float           # meta-analytic mean across replicates
    verdict: str
    replicate_effects: list[float] | None = None   # per-replicate, when replications > 1

    @property
    def refuted(self) -> bool:
        return self.verdict == REFUTED


@dataclass
class DiscoveryRun:
    """The full trace. Lands in `raw/` — non-authoritative by construction."""
    world_id: str
    strategy: str
    experiments: list[Experiment] = field(default_factory=list)
    model: dict[str, float] = field(default_factory=dict)   # "cause->effect" -> effect size

    @property
    def refutations(self) -> list[Experiment]:
        return [e for e in self.experiments if e.refuted]

    def to_dict(self) -> dict:
        return {
            "world_id": self.world_id,
            "strategy": self.strategy,
            "experiments": [asdict(e) for e in self.experiments],
            "model": self.model,
            "refutation_count": len(self.refutations),
        }


def _observational_sign(observations: list[dict], cause: str, effect: str) -> int:
    """What passive data *suggests*. On confounded worlds this is a trap, by design."""
    import statistics as st
    try:
        c = st.correlation([r[cause] for r in observations], [r[effect] for r in observations])
    except (st.StatisticsError, ValueError):
        return 0
    return 1 if c > 0 else (-1 if c < 0 else 0)


def run_discovery(world: World, reasoner: Reasoner, strategy: Strategy,
                  seed: int = 0) -> DiscoveryRun:
    variables = list(world.observable)
    observations = world.observe(strategy.samples_per_arm, seed=seed + 1)
    run = DiscoveryRun(world_id=world.world_id, strategy=strategy.name)

    for cause, effect in reasoner.rank_candidates(variables, observations, strategy):
        # 1. Commit the prediction. Drawn from observation — which is exactly why it
        #    can be wrong, and why the experiment is worth running.
        sign = _observational_sign(observations, cause, effect)
        hyp = Hypothesis(cause, effect, sign, "observational association")

        # 2. Run the experiment that can refute it — replicated. Replicate 0 uses the
        #    historical seed exactly, so replications=1 reproduces every past run
        #    bit-for-bit; further replicates draw fresh seeds. Samples per arm guard
        #    against sampling noise; replication guards against what samples cannot —
        #    the lucky seed. Paired arms share noise within a replicate as before.
        lo, hi = strategy.contrast
        arm_b = 0 if strategy.paired_arms else 1
        effects = []
        for r in range(max(1, strategy.replications)):
            rep_seed = seed + 2 if r == 0 else seed + 2 + 7919 * r
            a = _mean(world.intervene(cause, lo, strategy.samples_per_arm,
                                      seed=rep_seed), effect)
            b = _mean(world.intervene(cause, hi, strategy.samples_per_arm,
                                      seed=rep_seed, arm=arm_b), effect)
            effects.append((b - a) / (hi - lo))
        measured = sum(effects) / len(effects)

        # 3. Verdict by meta-analysis, not by self-report: the mean must clear the
        #    threshold AND a majority of replicates must agree on its sign — one
        #    lucky draw cannot carry a verdict once replications > 1.
        observed_sign = 1 if measured > strategy.effect_threshold else (
            -1 if measured < -strategy.effect_threshold else 0)
        agreeing = sum(1 for v in effects
                       if observed_sign != 0 and (v > 0) == (observed_sign > 0))
        consistent = observed_sign != 0 and agreeing * 2 > len(effects)
        verdict = SUPPORTED if consistent and observed_sign == sign else REFUTED

        run.experiments.append(Experiment(
            hyp, lo, hi, strategy.samples_per_arm, round(measured, 4), verdict,
            replicate_effects=([round(v, 4) for v in effects]
                               if len(effects) > 1 else None)))
        if observed_sign != 0:
            run.model[f"{cause}->{effect}"] = round(measured, 4)

    return run


def score_on_held_out(world: World, run: DiscoveryRun,
                      probes: list[tuple[str, float]], seed: int = 777) -> dict:
    """Predict held-out interventions the run never saw. Objective, no judge needed."""
    errors, correct_dir, total = [], 0, 0
    zero: dict[str, list[dict]] = {}
    for var, value in probes:
        if var not in world.observable:
            raise KeyError(f"probe names a non-observable variable: {var}")
        if var not in zero:
            zero[var] = world.intervene(var, 0.0, 400, seed=seed)
        moved = world.intervene(var, value, 400, seed=seed)
        for effect in world.observable:
            if effect == var:
                continue
            predicted = run.model.get(f"{var}->{effect}", 0.0) * value
            truth = _mean(moved, effect) - _mean(zero[var], effect)
            errors.append(abs(predicted - truth))
            # A null effect predicted as null counts as correct; sign agreement otherwise.
            if predicted * truth > 0 or (abs(truth) < 0.1 and abs(predicted) < 0.1):
                correct_dir += 1
            total += 1
    return {
        "mae": round(sum(errors) / len(errors), 4) if errors else 0.0,
        "direction_accuracy": round(correct_dir / total, 4) if total else 0.0,
        "probes": total,
    }


def _mean(rows: list[dict[str, float]], key: str) -> float:
    return sum(r[key] for r in rows) / len(rows)


def simulation_data(world: World, run: DiscoveryRun, strategy: Strategy,
                    seed: int = 0, per_band: int = 40, max_experiments: int = 4) -> dict:
    """The raw draws behind a run, re-derived from the same seeds.

    The loop does not retain its samples; it does not need to, because every draw is
    seeded. This replays exactly the calls run_discovery made — same seeds, same
    order — so the data shown IS the data the run saw, guaranteed by determinism
    rather than by having remembered it.

    Bands: the observation phase, then lo/hi arms per experiment. Down-sampled to
    `per_band` rows and capped at `max_experiments` experiments for display; the
    caps are reported so truncation is never silent.
    """
    bands = []
    obs = world.observe(strategy.samples_per_arm, seed=seed + 1)
    bands.append({"label": "observe", "kind": "observe", "rows": obs[:per_band]})

    shown = run.experiments[:max_experiments]
    for e in shown:
        cause = e.hypothesis.cause
        lo_rows = world.intervene(cause, e.lo, strategy.samples_per_arm, seed=seed + 2)
        arm_b = 0 if strategy.paired_arms else 1
        hi_rows = world.intervene(cause, e.hi, strategy.samples_per_arm, seed=seed + 2,
                                  arm=arm_b)
        bands.append({"label": f"do({cause}={e.lo:g})", "kind": "lo",
                      "cause": cause, "value": e.lo, "rows": lo_rows[:per_band]})
        bands.append({"label": f"do({cause}={e.hi:g})", "kind": "hi",
                      "cause": cause, "value": e.hi, "rows": hi_rows[:per_band]})

    return {
        "variables": list(world.observable),
        "per_band": per_band,
        "experiments_shown": len(shown),
        "experiments_total": len(run.experiments),
        "bands": bands,
    }
