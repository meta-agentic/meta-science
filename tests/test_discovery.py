"""Tests for the discovery loop.

The loop's integrity rests on ordering: the prediction must exist before the experiment
that can kill it. A hypothesis recorded afterwards is a description.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.discovery import REFUTED, run_discovery, score_on_held_out  # noqa: E402
from metascience.reasoner import HeuristicReasoner  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402
from metascience.templates import TEMPLATE_IDS, generate  # noqa: E402


def _run(tid, seed=7, **kw):
    w = generate(seed, tid)
    return w, run_discovery(w, HeuristicReasoner(), Strategy(**kw), seed=seed)


def test_the_prediction_is_drawn_from_observation_not_from_the_result():
    """If predictions were read off the experiment, nothing could ever be refuted."""
    _, run = _run("T6")
    assert run.experiments
    for e in run.experiments:
        assert e.hypothesis.basis == "observational association"


def test_the_confounded_world_refutes_the_agent():
    w, run = _run("T6")
    assert run.refutations, "T6 must refute a prediction drawn from its correlation"
    killed = [e for e in run.experiments
              if e.hypothesis.predicted_sign < 0 < e.observed_effect]
    assert killed, "the sign inversion must show up as a refuted hypothesis"


def test_conclusions_come_only_from_interventions():
    """The model records the MEASURED effect, never the predicted one."""
    _, run = _run("T6")
    for key, value in run.model.items():
        match = [e for e in run.experiments
                 if f"{e.hypothesis.cause}->{e.hypothesis.effect}" == key]
        assert match and match[0].observed_effect == value


def test_every_template_produces_a_scorable_model():
    for tid in TEMPLATE_IDS:
        w, run = _run(tid)
        v = list(w.observable)
        sc = score_on_held_out(w, run, [(v[0], 0.5), (v[0], -0.5)], seed=99)
        assert sc["probes"] > 0
        assert 0.0 <= sc["direction_accuracy"] <= 1.0


def test_intervening_beats_observing_on_the_confounded_world():
    """The claim the whole project rests on, asserted rather than described."""
    w, run = _run("T6")
    cause, effect = w.observable
    measured = run.model.get(f"{cause}->{effect}") or run.model.get(f"{effect}->{cause}")
    assert measured is not None
    truth = w.causal_effect(cause, effect)
    if abs(truth) > 0.2:
        assert measured * truth > 0, "the intervening loop must get the true sign"


def test_the_budget_is_respected():
    _, run = _run("T3", max_experiments=4)
    assert len(run.experiments) <= 4


def test_a_probe_on_an_unknown_variable_is_rejected_loudly():
    """Silently scoring zero for a typo'd variable would flatter the results."""
    w, run = _run("T3")
    try:
        score_on_held_out(w, run, [("NOPE", 0.5)])
    except KeyError as exc:
        assert "non-observable" in str(exc)
    else:
        raise AssertionError("an unknown probe variable must raise")


def test_simulation_data_replays_the_exact_draws_of_the_run():
    """The lane chart's honesty claim: shown data IS the run's data, re-derived from
    the same seeds rather than remembered. Verify against a fresh world object so
    nothing is carried over but the seeds."""
    from metascience.discovery import simulation_data

    w1 = generate(7, "T3")
    run = run_discovery(w1, HeuristicReasoner(), Strategy(), seed=7)
    data = simulation_data(generate(7, "T3"), run, Strategy(), seed=7)

    # The observation band must equal a direct re-draw with the run's seed.
    again = generate(7, "T3").observe(Strategy().samples_per_arm, seed=8)
    assert data["bands"][0]["rows"] == again[:data["per_band"]]

    # In a do() band the intervened variable is pinned at the set value in EVERY row.
    for band in data["bands"][1:]:
        for row in band["rows"]:
            assert row[band["cause"]] == band["value"]

    # Truncation is reported, never silent.
    assert data["experiments_total"] == len(run.experiments)
    assert data["experiments_shown"] <= 4
