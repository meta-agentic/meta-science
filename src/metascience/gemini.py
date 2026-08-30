"""Gemini adapters for the two reasoning roles.

Both are deliberately narrow. The model ranks and proposes; it never scores, never sees
the held-out seeds, and never renders a verdict on its own work. Everything it returns
is treated as a proposal landing in `raw/` — non-authoritative until the gate says
otherwise. That is the invariant, and keeping the model's surface small is how it is
enforced rather than merely stated.
"""
from __future__ import annotations

import hashlib
import json
import statistics as st
import time

from google import genai
from google.genai import types

from .config import MODEL_CASCADE, api_key
from .strategy import Strategy, candidate_pairs

# Fields a challenger is allowed to move. Anything outside this is ignored, so a
# malformed or over-reaching proposal degrades to "no change" instead of corrupting
# the strategy.
TUNABLE = {
    "samples_per_arm": int,
    "effect_threshold": float,
    "max_experiments": int,
    "screen_observationally": bool,
}


def _client() -> genai.Client:
    return genai.Client(api_key=api_key())


# Recorded rather than swallowed. An earlier version caught every exception and moved
# on, which turned a 503 into "the model had nothing to say" — a real failure wearing
# the costume of an empty answer. Anything that goes wrong now surfaces here.
LAST_ERRORS: list[str] = []


def _generate(prompt: str, schema: dict, temperature: float = 0.2,
              model: str | None = None) -> dict:
    client = _client()
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=schema,
    )
    LAST_ERRORS.clear()
    for model in ((model,) if model else MODEL_CASCADE):
        for attempt in range(2):
            try:
                r = client.models.generate_content(model=model, contents=prompt, config=cfg)
                return json.loads(r.text)
            except Exception as exc:  # noqa: BLE001
                LAST_ERRORS.append(f"{model}: {type(exc).__name__}: {str(exc)[:120]}")
                if "503" not in str(exc) or attempt:
                    break          # only a transient overload is worth a second try
                time.sleep(1.5)
    raise RuntimeError("no Gemini model answered:\n  " + "\n  ".join(LAST_ERRORS))


class GeminiReasoner:
    """Ranks which (cause, effect) pairs are worth an experiment.

    Ranking only. The loop still concludes from interventions alone, so a bad ranking
    costs experiments — never correctness.
    """

    def rank_candidates(self, variables, observations, strategy: Strategy):
        pairs = candidate_pairs(variables)
        if len(observations) < 3:
            return pairs[: strategy.max_experiments]

        assoc = {}
        for a, b in pairs:
            try:
                assoc[f"{a}->{b}"] = round(
                    st.correlation([r[a] for r in observations],
                                   [r[b] for r in observations]), 3)
            except (st.StatisticsError, ValueError):
                assoc[f"{a}->{b}"] = 0.0

        prompt = (
            "You are choosing which causal hypotheses to test by experiment in an unknown "
            "system. Variables are opaque labels with no domain meaning.\n\n"
            f"Variables: {variables}\n"
            f"Observational correlations (associations only): {json.dumps(assoc)}\n\n"
            "Association is not causation and may even carry the opposite sign when a "
            "hidden common cause is present. Rank the directed pairs you would test first, "
            f"most informative first, at most {strategy.max_experiments}. "
            "Return {\"ranking\": [\"X1->X2\", ...]} using only the pairs listed."
        )
        schema = {"type": "object",
                  "properties": {"ranking": {"type": "array", "items": {"type": "string"}}},
                  "required": ["ranking"]}
        try:
            ranking = _generate(prompt, schema).get("ranking", [])
        except RuntimeError:
            # Ranking is an optimisation, not a correctness requirement: the loop still
            # concludes from interventions. Degrade to the default order and carry on.
            return pairs[: strategy.max_experiments]

        valid = {f"{a}->{b}": (a, b) for a, b in pairs}
        out = [valid[k] for k in ranking if k in valid]
        out += [p for p in pairs if p not in out]
        return out[: strategy.max_experiments]


class GeminiProposer:
    """Proposes a change to the strategy — the self-evolution step.

    It is given the champion's knobs and a description of where it did poorly. It is
    NOT given the held-out seeds, the benchmark, or the scoring function, so it cannot
    tune against the test it will be judged on.
    """

    def propose(self, champion: Strategy, notes: str = "") -> Strategy:
        prompt = (
            "You are improving the experiment-design strategy of an automated scientist "
            "that discovers causal structure by intervening on unknown systems.\n\n"
            f"Current strategy: {json.dumps({k: getattr(champion, k) for k in TUNABLE})}\n"
            f"Observed weaknesses: {notes or 'none reported'}\n\n"
            "It is scored on getting causal directions right MINUS the total measurement "
            "it spends (experiments x arms x samples). Buying accuracy with more samples "
            "therefore loses. Propose ONE change that gets equal or better answers for "
            "less measurement, or better answers for the same.\n\n"
            "Return {\"changes\": {field: value}, \"rationale\": \"...\"} using only these "
            f"fields: {list(TUNABLE)}."
        )
        # Every tunable is declared explicitly. Structured output returns {} for an
        # untyped object property, which silently produced empty proposals.
        schema = {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "object",
                    "properties": {
                        "samples_per_arm": {"type": "integer"},
                        "effect_threshold": {"type": "number"},
                        "max_experiments": {"type": "integer"},
                        "screen_observationally": {"type": "boolean"},
                    },
                },
                "rationale": {"type": "string"},
            },
            "required": ["changes", "rationale"],
        }
        result = _generate(prompt, schema, temperature=0.7)
        changes = {}
        for k, v in (result.get("changes") or {}).items():
            if k in TUNABLE:
                try:
                    changes[k] = TUNABLE[k](v)
                except (TypeError, ValueError):
                    continue        # unusable value => simply not proposed
        # Same reason as the world generator: a builtin hash would give the identical
        # proposal a different name in each process, breaking receipt lineage.
        digest = hashlib.sha256(json.dumps(changes, sort_keys=True).encode()).hexdigest()
        name = f"gemini-{int(digest[:8], 16) % 10000:04d}"
        child = champion.child(name, **changes)
        object.__setattr__(child, "_rationale", result.get("rationale", ""))
        return child
