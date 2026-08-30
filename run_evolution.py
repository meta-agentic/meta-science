"""Demonstrate the gate in both directions: one refusal, one promotion."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.evolution import (ScriptedProposer, evaluate_strategy,  # noqa: E402
                                   held_out_seeds, run_generation)
from metascience.ledger import FileLedger, PromotionGate  # noqa: E402
from metascience.strategy import Strategy  # noqa: E402

seeds = held_out_seeds(24)
ledger = FileLedger("runs")
gate = PromotionGate(ledger, lambda s, ws: evaluate_strategy(s, ws), margin=0.02)

champion = Strategy()
print(f"champion {champion.name}: {evaluate_strategy(champion, seeds):+.4f}\n")

proposer = ScriptedProposer([
    # Deliberately bad: raises the bar so high that real effects are dismissed.
    ("blunt-v2", {"effect_threshold": 2.5}),
    # Genuinely better: same conclusions on a quarter of the measurement.
    ("frugal-v2", {"samples_per_arm": 100}),
])

for _ in range(2):
    champion, receipt = run_generation(ledger, gate, champion, proposer, seeds)
    print(f"{receipt.verdict:9s} {receipt.candidate:12s} "
          f"champ={receipt.champion_score:+.4f} chal={receipt.challenger_score:+.4f}")
    print(f"          diff={receipt.diff}")
    print(f"          {receipt.reason}")
    print(f"          receipt {receipt.digest()}\n")

print("canon now holds:", ledger.canon().get("strategy", "(unchanged — champion-v1)"))
