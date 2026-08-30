"""One turn of the wheel, driven by Gemini.

Gemini proposes a change to the scientist's own method. It never sees the held-out
worlds, never computes the score, and has no say in the verdict. The gate runs the
evidence and decides.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env  # noqa: E402
from metascience.evolution import (ScriptedProposer, evaluate_strategy,  # noqa: E402
                                   held_out_seeds, run_generation)
from metascience.gemini import GeminiProposer  # noqa: E402
from metascience.ledger import FileLedger, PromotionGate  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--generations", type=int, default=3)
ap.add_argument("--offline", action="store_true", help="scripted proposer, no API calls")
args = ap.parse_args()

load_env()
seeds = held_out_seeds(24)
ledger = FileLedger("runs")
gate = PromotionGate(ledger, evaluate_strategy, margin=0.02)
proposer = (ScriptedProposer([("blunt-v2", {"effect_threshold": 2.5}),
                              ("frugal-v2", {"samples_per_arm": 100})])
            if args.offline else GeminiProposer())

champion = Strategy()
print(f"held-out worlds: {len(seeds)}  (never shown to the proposer)")
print(f"champion {champion.name}: {evaluate_strategy(champion, seeds):+.4f}\n")

notes = "accuracy is saturated on most worlds; the strategy spends 12 experiments x 400 samples each"
for i in range(args.generations):
    champion, r = run_generation(ledger, gate, champion, proposer, seeds, notes)
    mark = "✓" if r.verdict == "PROMOTED" else "✗"
    print(f"gen {i+1}  {mark} {r.verdict:9s} {r.candidate}")
    print(f"         diff   {r.diff}")
    print(f"         champ {r.champion_score:+.4f}  challenger {r.challenger_score:+.4f}")
    print(f"         {r.reason}")
    print(f"         receipt {r.digest()}\n")
    notes = (f"{r.candidate} scored {r.challenger_score:+.4f} against champion "
             f"{r.champion_score:+.4f}. Verdict {r.verdict}.")

print("canon:", ledger.canon().get("strategy", {}).get("name", "champion-v1 (unchanged)"))
