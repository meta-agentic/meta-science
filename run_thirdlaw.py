"""The third-law experiment: eight planets, one law, full traces.

Eight fictional planets propagated around the Sun by the flight-dynamics service;
period and semi-major axis measured from each trajectory (wrap time and geometry —
never injected). The agent gets the anonymised (x1, x2) table, non-cyclic this
time, and must compose the law free-form. The exponent is the discovery: it is
invariant under the anonymising rescale, so nothing about the disguise can hand
it over.

Every Gemini exchange is recorded whole — prompt, raw answer, answering model,
transport errors, timestamps — because the reasoning is data now.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from metascience.config import load_env  # noqa: E402
from metascience import ephemeris, laws  # noqa: E402

A_SCALE, T_SCALE = 0.73, 0.41

table = ephemeris.third_law_table()
rows = [(round(r["a_au"] * A_SCALE, 5), round(r["period_days"] * T_SCALE, 5))
        for r in table]
print(f"{'seed':>4} {'a (AU)':>8} {'T (days)':>9}   -> blind (x1, x2)")
for r, (x1, x2) in zip(table, rows):
    print(f"{r['seed']:>4} {r['a_au']:>8.4f} {r['period_days']:>9.2f}   -> "
          f"({x1}, {x2})")

if "--offline" in sys.argv:
    sys.exit(0)

load_env()
from metascience import gemini  # noqa: E402

trace = {"experiment": "third-law", "planets": table,
         "scales": {"x1": A_SCALE, "x2": T_SCALE}, "exchanges": []}


def ask(prompt: str) -> dict:
    t0 = time.time()
    answer = gemini._generate(prompt, laws.FREEFORM_SCHEMA)
    trace["exchanges"].append({
        "prompt": prompt,
        "answer": answer,
        "model": gemini.LAST_MODEL,
        "transport_errors": list(gemini.LAST_ERRORS),
        "seconds": round(time.time() - t0, 2),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    return answer


shown = rows[:3] + rows[4:]                      # hold out one mid-fleet planet
held = rows[3]
answer = ask(laws.freeform_prompt(shown, held[0], cyclic=False))
scored = laws.score(answer["expression"], rows, stride=4)
trace["round1_scored"] = scored
print("\n=== round 1 (free-form, blind) ===")
print("  expression :", answer["expression"])
print("  claimed    :", answer["claimed_source"])
print("  rationale  :", answer["rationale"][:180])
print("  constants  :", scored.get("constants"))
print("  holdout    :", scored.get("holdout_mean_abs_err"))

# One refinement round if the shape missed, with residual feedback — the same
# loop that took the first-law probe from cosine to conic.
if scored.get("holdout_mean_abs_err") is None or \
        scored["holdout_mean_abs_err"] > 0.2:
    tree = laws.parse(answer["expression"])
    resid = []
    for x1, x2 in rows:
        try:
            r = x2 - laws.evaluate(tree, {"x1": x1, **scored["constants"]})
        except Exception:
            r = None
        resid.append((x1, None if r is None else round(r, 5)))
    rtable = "\n".join(f"  x1={a}   residual={b}" for a, b in resid)
    answer2 = ask(
        "You previously proposed  x2 = " + answer["expression"] + "  with fitted "
        f"constants {scored['constants']}. The residuals (measured minus "
        "predicted) are systematic:\n\n" + rtable + "\n\n"
        "Refine the law. Same grammar: numbers, x1, free constants c1..c4 "
        "(fitted for you), pi, + - * / parentheses, cos sin exp log sqrt abs "
        "pow(base, exponent). Change the SHAPE. Say what physical system, if "
        "any, you now believe produced this data, and one sentence of rationale.")
    scored2 = laws.score(answer2["expression"], rows, stride=4)
    trace["round2_scored"] = scored2
    print("\n=== round 2 (residual feedback) ===")
    print("  expression :", answer2["expression"])
    print("  claimed    :", answer2["claimed_source"])
    print("  constants  :", scored2.get("constants"))
    print("  holdout    :", scored2.get("holdout_mean_abs_err"))

out = Path("runs") / "kepler"
out.mkdir(parents=True, exist_ok=True)
path = out / f"{int(time.time())}-thirdlaw.json"
path.write_text(json.dumps(trace, indent=2))
print(f"\nfull trace: {path}")
