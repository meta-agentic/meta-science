"""The Kepler test: law induction from Tycho Brahe's Mars data, run twice.

Once blind — anonymised coordinates, a cyclic x1, unstated units — and once labelled,
with Mars, Tycho and Kepler named in full. Each arm asks for the same four things:
does x2 depend on x1, which functional family, a committed prediction for a held-out
point, and what physical system the model believes it is looking at. The gap between
the two arms is a measurement of recall on the one dataset where memorisation is
guaranteed.

Offline (--offline) prints the geometry and the family fits and makes no API call.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env  # noqa: E402
from metascience import kepler  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--offline", action="store_true", help="geometry and fits only")
args = ap.parse_args()

print("Triangulated heliocentric positions of Mars (theta deg, r AU):")
for (t, r), pair in zip(kepler.mars_points(), kepler.TYCHO_PAIRS):
    print(f"  {pair[0][0]} + {pair[1][0]}   theta {t:7.2f}   r {r:.4f}")

print("\nFull fits on all five points:")
fits = kepler.full_fits()
for name, params in fits.items():
    print(f"  {name:14s} {params}")

print("\nLeave-one-out held-out error (AU):")
loo = kepler.leave_one_out()
for name, e in sorted(loo.items(), key=lambda kv: kv[1]["mean_abs_err"]):
    print(f"  {name:14s} mean {e['mean_abs_err']:.4f}   worst {e['worst_abs_err']:.4f}")

if args.offline:
    sys.exit(0)

load_env()
out_dir = Path("runs") / "kepler"
out_dir.mkdir(parents=True, exist_ok=True)
record = {"fits": fits, "leave_one_out": loo, "arms": {}}

for blind in (True, False):
    arm = "blind" if blind else "labelled"
    print(f"\n=== {arm} arm ===")
    result = kepler.blind_inference(blind=blind)
    record["arms"][arm] = result
    m = result["model"]
    print(f"  depends on x1 : {m['depends_on_x1']}")
    print(f"  family        : {m['family']}")
    print(f"  predicted x2  : {m['predicted_x2']}   (measured {result['held_out']['x2']},"
          f" |err| {result['abs_error']} = {result['abs_error_au']} AU)")
    print(f"  claimed source: {m['claimed_source']}")
    print(f"  rationale     : {m['rationale']}")
    print(f"  harness preds : {result['harness_predictions']}")
    print(f"  beats constant: {result['beats_constant']}")
    time.sleep(2)

stamp = int(time.time())
path = out_dir / f"{stamp}-kepler-test.json"
path.write_text(json.dumps(record, indent=2))
print(f"\nrecord: {path}")
