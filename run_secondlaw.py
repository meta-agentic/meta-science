"""The second-law experiment: swept area against time, in two worlds.

Arm A is a fictional planet under two-body forces: the swept area grows exactly
linearly with time — Kepler's second law. Arm B is the drag world: a dissipative
force bleeds angular momentum and the sweep falls behind its own line.

Both arms run the same two rounds. Round 1: blind rows of (x1=time, x2=swept
area), free-form law. Round 2: the model sees its law's residuals and must decide
whether they are noise (keep the law unchanged — the correct answer for arm A) or
structure (refine — the correct answer for arm B). A system that can only ever
refine cannot be trusted when it does; the keep option is what makes the refine
informative.

Every exchange is recorded whole. Records land in runs/kepler/ and are curated
into docs/secondlaw/.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env  # noqa: E402
from metascience import ephemeris, laws  # noqa: E402

T_SCALE = 0.41

arms = {}
for arm, series_fn in (("equal_areas", ephemeris.equal_areas_series),
                       ("drag", ephemeris.drag_series)):
    series = series_fn()
    area = ephemeris.swept_area(series)
    a_scale = 10.0 / area[-1][1]
    rows = [(round(t * T_SCALE, 5), round(a * a_scale, 5)) for t, a in area]
    rates = ephemeris.areal_rates(series)
    k = max(1, len(rates) // 10)
    drift = (sum(rates[-k:]) / k - sum(rates[:k]) / k) / (sum(rates[:k]) / k)
    arms[arm] = {"rows": rows, "a_scale": a_scale, "drift_pct": round(100 * drift, 4)}
    print(f"{arm:12s} {len(rows)} rows, areal-rate drift {100*drift:+.4f}%")

if "--offline" in sys.argv:
    sys.exit(0)

load_env()
from metascience import gemini  # noqa: E402

trace = {"experiment": "second-law", "t_scale": T_SCALE, "arms": {}}


def ask(prompt: str) -> dict:
    t0 = time.time()
    answer = gemini._generate(prompt, laws.FREEFORM_SCHEMA)
    entry = {"prompt": prompt, "answer": answer, "model": gemini.LAST_MODEL,
             "transport_errors": list(gemini.LAST_ERRORS),
             "seconds": round(time.time() - t0, 2),
             "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    trace["arms"].setdefault(arm, {"exchanges": []})["exchanges"].append(entry)
    return answer


for arm in ("equal_areas", "drag"):
    rows = arms[arm]["rows"]
    step = max(1, len(rows) // 12)
    shown = rows[::step][:12]
    held = rows[len(rows) * 2 // 3]
    print(f"\n=== {arm}: round 1 (free-form, blind) ===")
    a1 = ask(laws.freeform_prompt(shown, held[0], cyclic=False))
    s1 = laws.score(a1["expression"], rows, stride=4)
    trace["arms"][arm]["round1_scored"] = s1
    print("  expression :", a1["expression"])
    print("  claimed    :", a1["claimed_source"])
    print("  constants  :", s1.get("constants"))
    print("  holdout    :", s1.get("holdout_mean_abs_err"))

    tree = laws.parse(a1["expression"])
    resid = []
    for x1, x2 in rows[::step][:16]:
        try:
            r = round(x2 - laws.evaluate(tree, {"x1": x1, **s1["constants"]}), 5)
        except Exception:
            r = None
        resid.append((x1, r))
    rtable = "\n".join(f"  x1={a}   residual={b}" for a, b in resid)
    print(f"=== {arm}: round 2 (residual review) ===")
    a2 = ask(
        "You proposed  x2 = " + a1["expression"] + "  for measured data, with "
        f"fitted constants {s1['constants']}. Below are the residuals (measured "
        "minus predicted). Decide whether they are measurement noise or a "
        "systematic pattern.\n\n" + rtable + "\n\n"
        "If they are noise, return EXACTLY the same expression unchanged — do not "
        "invent structure that is not there. If they are systematic, refine the "
        "law. Same grammar: numbers, x1, free constants c1..c4 (fitted for you), "
        "pi, + - * / parentheses, cos sin exp log sqrt abs pow(base, exponent). "
        "Then say what physical system, if any, you believe produced this data, "
        "and one sentence of rationale.")
    s2 = laws.score(a2["expression"], rows, stride=4)
    trace["arms"][arm]["round2_scored"] = s2
    changed = a2["expression"].replace(" ", "") != a1["expression"].replace(" ", "")
    trace["arms"][arm]["changed_in_round2"] = changed
    print("  expression :", a2["expression"], "(changed)" if changed else "(kept)")
    print("  claimed    :", a2["claimed_source"])
    print("  rationale  :", a2["rationale"][:170])
    print("  constants  :", s2.get("constants"))
    print("  holdout    :", s2.get("holdout_mean_abs_err"))
    time.sleep(2)

out = Path("runs") / "kepler"
out.mkdir(parents=True, exist_ok=True)
path = out / f"{int(time.time())}-secondlaw.json"
path.write_text(json.dumps(trace, indent=2))
print(f"\nfull trace: {path}")
