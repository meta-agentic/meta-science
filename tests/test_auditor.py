"""The auditor must discriminate, not just be suspicious.

A detector that fires on every promotion carries exactly as much information as one that
fires on none. Both of these cases must come out differently, or the auditor is theatre.
"""
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.config import load_env  # noqa: E402
from metascience.ledger import Receipt  # noqa: E402

load_env(Path(__file__).resolve().parents[1] / ".env")
pytestmark = [
    pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="needs GEMINI_API_KEY"),
    pytest.mark.slow,   # two live calls to the auditor model
]

TUNABLES = {"samples_per_arm": "int", "effect_threshold": "float",
            "max_experiments": "int", "screen_observationally": "bool"}


def _receipt(name, diff, champ, chal):
    return Receipt("PROMOTED", name, "champion-v1", diff, champ["score"], chal["score"],
                   0.02, [1, 2, 3], "beat margin", time.time(), champ, chal)


CHAMPION = {"score": 0.8704, "accuracy": 1.0, "cost": 0.1296, "worlds": 24}


def test_an_efficiency_gain_within_noise_is_not_flagged():
    """Same answers for a quarter of the measurement is good science, not a trick."""
    from metascience.auditor import audit_promotion
    r = _receipt("frugal", {"samples_per_arm": (100, 400)}, CHAMPION,
                 {"score": 0.9537, "accuracy": 0.9861, "cost": 0.0324, "worlds": 24})
    assert audit_promotion(r, TUNABLES)["legitimate"] is True


def test_accuracy_traded_away_for_cost_is_flagged():
    """The failure mode the auditor exists for: the saving outrunning a real loss."""
    from metascience.auditor import audit_promotion
    r = _receipt("sneaky", {"samples_per_arm": (5, 400)}, CHAMPION,
                 {"score": 0.8950, "accuracy": 0.8966, "cost": 0.0016, "worlds": 24})
    assert audit_promotion(r, TUNABLES)["legitimate"] is False


def test_an_unavailable_auditor_is_recorded_as_absent_not_as_approval():
    """Silence must never read as consent — offline, that is the whole risk."""
    import metascience.auditor as aud
    original = aud.AUDITOR_MODELS
    aud.AUDITOR_MODELS = ("model-that-does-not-exist",)
    try:
        out = aud.audit_promotion(_receipt("x", {}, CHAMPION, CHAMPION), TUNABLES)
    finally:
        aud.AUDITOR_MODELS = original
    assert out["legitimate"] is None, "unavailable must not become True"
    assert "unavailable" in out["concern"]
