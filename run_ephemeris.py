"""The propagated arms of the Kepler test.

Three worlds from the isohub flight-dynamics service: a fictional planet under pure
two-body forces (unmemorisable — real physics, no textbook), the same machinery
around an oblate primary (the textbook answer is wrong there), and the two-body
control for that orbit. Offline, prints the held-out comparison from the recorded
fixtures. Live (default), also asks Gemini the blind questions about the fictional
planet — the recall probe with nothing to recall.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env  # noqa: E402
from metascience import ephemeris, kepler  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--offline", action="store_true", help="fixture analysis only")
args = ap.parse_args()

WORLDS = {
    "unmemorisable planet": ephemeris.unmemorisable(7),
    "control orbit": ephemeris.control_orbit(7),
    "oblate (law-breaking)": ephemeris.law_breaking(7),
}

for name, pts in WORLDS.items():
    score = kepler.holdout_score(pts)
    best = min(score, key=lambda k: score[k]["mean_abs_err"])
    conic = kepler.fit_focus_conic(pts)[0]
    print(f"=== {name} ===  {len(pts)} points, best family: {best}")
    for fam, e in sorted(score.items(), key=lambda kv: kv[1]["mean_abs_err"]):
        print(f"  {fam:14s} mean {e['mean_abs_err']:.5f}  worst {e['worst_abs_err']:.5f}")
    print(f"  conic: e={conic['e']}  theta0={conic['theta0_deg']}")

if args.offline:
    sys.exit(0)

load_env()
from metascience.gemini import _generate  # noqa: E402

points = WORLDS["unmemorisable planet"]
shown = points[::12][:11]                       # a spread of rows, one held out
held = points[7 * 12 // 2]                      # a point the subsample skips
rows = "\n".join(
    f"  x1={round(t / 360.0, 5)}   x2={round(r * kepler.BLIND_SCALE, 5)}"
    for t, r in shown)
prompt = (
    "Eleven measured rows of two variables. x1 is a cyclic coordinate with period 1 "
    "(x1=0 and x1=1 are the same place). x2 is a positive measured quantity in fixed "
    "but unstated units. Nothing else about the source of this data is "
    "available.\n\n" + rows + "\n\n"
    "Task, in order:\n"
    "1. Does x2 depend on x1?\n"
    "2. Propose the functional family. One of: constant, cosine (a + b*cos(angle - "
    "phase)), offset_circle (a circle displaced from the origin of a polar "
    "coordinate system), focus_conic (r = p/(1 + e*cos(angle - phase)), origin at "
    "a focus).\n"
    f"3. Predict x2 at x1={round(held[0] / 360.0, 5)}. Commit to a number.\n"
    "4. Say what specific physical system, if any, you believe produced this data — "
    "name it if you can name it. If you cannot, say so.\n"
    "5. One sentence of rationale.")

answer = _generate(prompt, kepler.PROPOSAL_SCHEMA)
err = abs(answer["predicted_x2"] - held[1] * kepler.BLIND_SCALE)
record = {
    "world": "unmemorisable planet, seed 7",
    "model": answer,
    "held_out": {"x1": round(held[0] / 360.0, 5),
                 "x2": round(held[1] * kepler.BLIND_SCALE, 5)},
    "abs_error": round(err, 5),
}
print("\n=== blind probe, unmemorisable planet ===")
for k in ("depends_on_x1", "family", "predicted_x2", "claimed_source", "rationale"):
    print(f"  {k:14s}: {answer[k]}")
print(f"  measured      : {record['held_out']['x2']}   |err| {record['abs_error']}")

out = Path("runs") / "kepler"
out.mkdir(parents=True, exist_ok=True)
path = out / f"{int(time.time())}-ephemeris-probe.json"
path.write_text(json.dumps(record, indent=2))
print(f"\nrecord: {path}")
