#!/usr/bin/env python3
"""Independent validation of the evidence page's design rationale.

Same discipline as the promotion gate: the designer does not grade their own work.
The full rationale and the actual figure data go to a Gemini model with an adversarial
brief — find the weakest encoding choice, the most misleading element, the claim the
figures do not support. The verdict is recorded whichever way it lands.

    python3 scripts/validate_viz.py            # writes docs/viz-validation.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience.config import load_env  # noqa: E402

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["SOUND", "SOUND_WITH_CONCERNS", "FLAWED"]},
        "figures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "figure": {"type": "integer"},
                    "encoding_correct": {"type": "boolean"},
                    "reasoning_holds": {"type": "boolean"},
                    "concern": {"type": "string"},
                    "severity": {"type": "string", "enum": ["none", "minor", "major"]},
                },
                "required": ["figure", "encoding_correct", "reasoning_holds",
                             "concern", "severity"],
            },
        },
        "misleading_risk": {"type": "string"},
        "strongest_objection": {"type": "string"},
    },
    "required": ["verdict", "figures", "misleading_risk", "strongest_objection"],
}


def main() -> None:
    load_env(ROOT / ".env")
    from metascience.gemini import _generate

    rationale = (ROOT / "docs" / "viz-rationale.md").read_text()
    study = json.loads((ROOT / "static" / "study.json").read_text())

    prompt = (
        "You are reviewing the design of a scientific results page. You did not design "
        "it, you owe its authors nothing, and your job is to find what is wrong.\n\n"
        "Below are (1) the designers' stated rationale for four figures and (2) the "
        "actual data the figures render. Attack the reasoning: is each encoding the "
        "right one for the data type and the reader's task? Does any figure risk "
        "misleading a careful reader? Is any claim in the rationale unsupported by the "
        "data provided? Perceptual-accuracy arguments (position > length > angle > "
        "area) and baseline/axis honesty are in scope.\n\n"
        "Do not manufacture objections to seem rigorous: a sound choice is called "
        "sound. But a real flaw stated politely is still FLAWED.\n\n"
        f"--- RATIONALE ---\n{rationale}\n\n"
        f"--- FIGURE DATA ---\n{json.dumps(study, indent=1)}\n"
    )
    result = _generate(prompt, SCHEMA, temperature=0.2)

    lines = [
        "# Evidence page — validation verdict",
        "",
        "Produced by `scripts/validate_viz.py`: the rationale and the actual figure",
        "data were given to an independent Gemini reviewer with an adversarial brief.",
        "Recorded verbatim, whichever way it landed.",
        "",
        f"**Verdict: {result['verdict']}**",
        "",
        f"- **Strongest objection**: {result['strongest_objection']}",
        f"- **Misleading risk**: {result['misleading_risk']}",
        "",
        "| figure | encoding | reasoning | severity | concern |",
        "|---|---|---|---|---|",
    ]
    for f in sorted(result["figures"], key=lambda x: x["figure"]):
        lines.append(
            f"| {f['figure']} | {'ok' if f['encoding_correct'] else 'WRONG'} "
            f"| {'holds' if f['reasoning_holds'] else 'FAILS'} "
            f"| {f['severity']} | {f['concern'] or '—'} |")
    (ROOT / "docs" / "viz-validation.md").write_text("\n".join(lines) + "\n")
    print(f"verdict: {result['verdict']}")
    for f in sorted(result["figures"], key=lambda x: x["figure"]):
        print(f"  fig {f['figure']}: {f['severity']:5s} — {f['concern'][:110]}")
    print(f"\nstrongest objection: {result['strongest_objection'][:200]}")


if __name__ == "__main__":
    main()
