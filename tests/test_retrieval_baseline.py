"""The adversarial test of anonymisation.

Everything else checks that domain terms do not *appear*. This checks the thing that
actually matters: that a model given the anonymised surface cannot recover the answer
without experimenting. If it can, the benchmark measures recall and every downstream
number is void.

Needs an API key. Skipped without one, so the rest of the suite stays offline.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.config import load_env  # noqa: E402
from metascience.templates import generate  # noqa: E402

load_env(Path(__file__).resolve().parents[1] / ".env")
pytestmark = [
    pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="needs GEMINI_API_KEY"),
    pytest.mark.slow,   # three live calls with large observation payloads
]


def _ask_sign(world, cause, effect, observations) -> int:
    """Ask for a causal direction from observation alone. No interventions offered."""
    import json

    from metascience.gemini import _generate

    rows = json.dumps(observations[:60])
    prompt = (
        "Below are passive observations of an unknown system. You may NOT run experiments.\n\n"
        f"Variables: {list(world.observable)}\n"
        f"Observations: {rows}\n\n"
        f"State the sign of the CAUSAL effect of {cause} on {effect}: "
        "1 if increasing it increases the other, -1 if it decreases it, 0 if no effect.\n"
        'Return {"sign": 1|-1|0, "confidence": 0.0-1.0}.'
    )
    schema = {"type": "object",
              "properties": {"sign": {"type": "integer"},
                             "confidence": {"type": "number"}},
              "required": ["sign", "confidence"]}
    return int(_generate(prompt, schema, temperature=0.0).get("sign", 0))


def test_observation_alone_cannot_recover_the_confounded_law():
    """On T6 the correlation is negative and the true effect positive.

    A model reading only observations should follow the correlation and get it WRONG.
    That failure is the evidence that intervention is doing the work — if the model
    were right here, the agent's experiments would be decoration.
    """
    wrong = 0
    trials = [0, 7, 13]
    for seed in trials:
        w = generate(seed, "T6")
        cause, effect = w.observable
        obs = w.observe(400, seed=1)
        said = _ask_sign(w, cause, effect, obs)
        truth = 1 if w.causal_effect(cause, effect) > 0 else -1
        if said != truth:
            wrong += 1
    # If observation alone were sufficient, this would be 0.
    assert wrong >= 2, (
        f"observation-only recovered the causal sign in {len(trials) - wrong}/{len(trials)} "
        "confounded worlds — intervention is not doing the work the design assumes"
    )
