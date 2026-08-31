"""The repetition campaign: n=30 for every live claim in both papers.

Every experiment so far ran once; a paper cannot stand on n=1. This script
repeats each live arm thirty times, checkpointing every repetition to its own
JSON file the moment it completes — a quota error or a killed process loses at
most one repetition, and re-running skips whatever exists.

Arms (all proposals live; all scoring offline and deterministic):

  B1 recall     - free-form law on Tycho's Mars points, blind vs labeled, and
                  on the synthetic planet, blind. Measures the recognition
                  rate (does the model name Kepler/Mars?) and the scored law,
                  per arm.
  B2 refine     - first law on the synthetic planet: round 1 free-form; if the
                  judge refuses, round 2 with residual feedback. Measures the
                  round-1 shape distribution and the conversion rate.
  B3 thirdlaw   - one shot on the eight-planet (a, T) table. Measures the
                  fitted exponent of the model's own expression and the
                  claimed source.
  B4 secondlaw  - both arms (equal-areas planet / drag), round 1 plus a
                  residual review whose correct answer differs by arm.
                  Measures keep/refine correctness.
  A  evolution  - a full three-generation gated self-evolution run per
                  repetition, with live proposer and auditor. Measures the
                  verdict pattern, margins, and auditor agreement.

Temperature is the harness default (0.2) — the variance measured here is the
variance a user of the system would actually see. Rate limits are respected by
a campaign-level backoff on quota errors; transport failures are recorded, not
retried into silence.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metascience.config import load_env  # noqa: E402

load_env()

from metascience import ephemeris, gemini, kepler, laws  # noqa: E402

OUT = ROOT / "runs" / "campaign"
REPS = 30


MIN_INTERVAL = 8.0   # seconds between call STARTS: stay well under the RPM cap
_last_call = [0.0]   # a naive backoff ladder made things worse — every retry
                     # hits up to four endpoints (two models x two attempts),
                     # feeding the throttle it is waiting out. Pace, don't retry.

# The evolution arm's proposer and auditor reach _generate directly, not through
# _ask — pace every caller at the source. Both resolve the symbol at call time,
# so patching the module attribute covers them.
_orig_generate = gemini._generate


def _paced_generate(*args, **kwargs):
    wait = _last_call[0] + MIN_INTERVAL - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    return _orig_generate(*args, **kwargs)


gemini._generate = _paced_generate


def _ask(prompt: str, schema: dict) -> dict:
    """One live call, paced below the rate limit, with a full trace."""
    for attempt in range(8):
        wait = _last_call[0] + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.time()
        t0 = time.time()
        try:
            answer = gemini._generate(prompt, schema)
            return {"prompt": prompt, "answer": answer, "model": gemini.LAST_MODEL,
                    "seconds": round(time.time() - t0, 2),
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        except RuntimeError as exc:
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
                wait = 60 + 30 * attempt
                print(f"    quota backoff {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("quota backoff exhausted")


def _checkpointed(arm: str, rep: int, fn):
    path = OUT / arm / f"rep-{rep:03d}.json"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    record = fn()
    record["rep"] = rep
    path.write_text(json.dumps(record, indent=1))
    return True


def _mentions_kepler(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in ("kepler", "mars", "planet", "orbit", "celestial",
                                "heliocentric", "astronom"))


def _safe_judge(expression: str, rows, stride=4) -> dict:
    try:
        return laws.judge(expression, rows, stride)
    except laws.LawSyntaxError as exc:
        return {"error": str(exc)}


# ------------------------------------------------------------------- B1: recall

TYCHO_BLIND = [(round(t / 360.0, 5), round(r * kepler.BLIND_SCALE, 5))
               for t, r in kepler.mars_points()]
TYCHO_LABELED = [(round(t, 3), round(r, 4)) for t, r in kepler.mars_points()]
SYNTH = [(round(t / 360.0, 5), round(r * kepler.BLIND_SCALE, 5))
         for t, r in ephemeris.unmemorisable(7)]


def _labeled_prompt(rows) -> str:
    table = "\n".join(f"  longitude={a} deg   distance={b} AU" for a, b in rows)
    return (
        f"{len(rows)} heliocentric positions of the planet Mars, triangulated "
        "from Tycho Brahe's observations by the 687-day method Kepler describes "
        "in Astronomia Nova. Columns: heliocentric longitude (degrees), Sun-Mars "
        "distance (astronomical units).\n\n" + table + "\n\n"
        "Task:\n"
        "1. Does the distance depend on the longitude?\n"
        "2. Write ONE mathematical expression for the distance as a function of "
        "x1, the longitude in DEGREES. You may use: numbers, x1, free constants "
        "c1 c2 c3 c4 (their values will be fitted for you), pi, + - * / "
        "parentheses, and the functions cos sin exp log sqrt abs pow(base, "
        "exponent). Nothing else.\n"
        "3. The expression will be judged on positions you have not seen.\n"
        "4. Say what physical system you believe produced this data.\n"
        "5. One sentence of rationale.")


def arm_b1(rep: int) -> bool:
    def run():
        rec = {}
        for name, rows, prompt in (
                ("tycho_blind", TYCHO_BLIND,
                 laws.freeform_prompt(sorted(TYCHO_BLIND)[:4],
                                      sorted(TYCHO_BLIND)[4][0])),
                ("tycho_labeled", TYCHO_LABELED,
                 _labeled_prompt(sorted(TYCHO_LABELED)[:4])),
                ("synth_blind", SYNTH,
                 laws.freeform_prompt(SYNTH[::13][:11], SYNTH[46][0]))):
            x = _ask(prompt, laws.FREEFORM_SCHEMA)
            expr = x["answer"]["expression"]
            rec[name] = {
                "exchange": x,
                "scored": _safe_judge(expr, rows),
                "recognises": _mentions_kepler(x["answer"]["claimed_source"]),
            }
            time.sleep(1)
        return rec
    return _checkpointed("b1-recall", rep, run)


# ----------------------------------------------------------------- B2: refinement

def arm_b2(rep: int) -> bool:
    def run():
        rows = SYNTH
        shown = rows[::13][:11]
        x1 = _ask(laws.freeform_prompt(shown, rows[46][0]), laws.FREEFORM_SCHEMA)
        s1 = _safe_judge(x1["answer"]["expression"], rows)
        rec = {"round1": {"exchange": x1, "scored": s1}}
        if "error" not in s1 and not s1["extrapolates"]:
            tree = laws.parse(x1["answer"]["expression"])
            consts = s1["interpolation"]["constants"]
            resid = []
            for a, b in shown:
                try:
                    resid.append((a, round(b - laws.evaluate(
                        tree, {"x1": a, **consts}), 6)))
                except Exception:
                    resid.append((a, None))
            rtable = "\n".join(f"  x1={a}   residual={b}" for a, b in resid)
            x2 = _ask(
                "You previously proposed  x2 = " + x1["answer"]["expression"] +
                f"  with fitted constants {consts}. The residuals (measured "
                "minus predicted) are systematic:\n\n" + rtable + "\n\n"
                "Refine the law. Same grammar: numbers, x1, free constants "
                "c1..c4 (fitted for you), pi, + - * / parentheses, cos sin exp "
                "log sqrt abs pow(base, exponent). Change the SHAPE. Say what "
                "physical system, if any, you now believe produced this data, "
                "and one sentence of rationale.", laws.FREEFORM_SCHEMA)
            rec["round2"] = {"exchange": x2,
                             "scored": _safe_judge(x2["answer"]["expression"],
                                                   rows)}
        return rec
    return _checkpointed("b2-refine", rep, run)


# ------------------------------------------------------------------ B3: third law

THIRD_ROWS = None


def arm_b3(rep: int) -> bool:
    global THIRD_ROWS
    if THIRD_ROWS is None:
        THIRD_ROWS = [(round(r["a_au"] * 0.73, 5), round(r["period_days"] * 0.41, 5))
                      for r in ephemeris.third_law_table()]

    def run():
        shown = THIRD_ROWS[:3] + THIRD_ROWS[4:]
        x = _ask(laws.freeform_prompt(shown, THIRD_ROWS[3][0], cyclic=False),
                 laws.FREEFORM_SCHEMA)
        expr = x["answer"]["expression"]
        rec = {"exchange": x, "scored": _safe_judge(expr, THIRD_ROWS)}
        # the exponent of the model's own law, measured by refitting a pure
        # power law is NOT what we want — extract it from the model's shape by
        # fitting its expression and reading pow(x1, c) if that is its form;
        # otherwise record the fitted constants as-is and let analysis decide.
        rec["mentions_kepler_or_cl"] = _mentions_kepler(
            x["answer"]["claimed_source"]) or "langmuir" in \
            x["answer"]["claimed_source"].lower() or "child" in \
            x["answer"]["claimed_source"].lower()
        return rec
    return _checkpointed("b3-thirdlaw", rep, run)


# ----------------------------------------------------------------- B4: second law

_SECOND = None


def _second_rows():
    global _SECOND
    if _SECOND is None:
        out = {}
        for arm, fn in (("equal_areas", ephemeris.equal_areas_series),
                        ("drag", ephemeris.drag_series)):
            series = fn()
            area = ephemeris.swept_area(series)
            a_scale = 10.0 / area[-1][1]
            rows = [(round(t * 0.41, 5), round(a * a_scale, 5)) for t, a in area]
            out[arm] = rows if arm == "equal_areas" else rows[::4]
        _SECOND = out
    return _SECOND


def arm_b4(rep: int) -> bool:
    def run():
        rec = {}
        for arm, rows in _second_rows().items():
            step = max(1, len(rows) // 12)
            shown = rows[::step][:12]
            x1 = _ask(laws.freeform_prompt(shown, rows[len(rows) * 2 // 3][0],
                                           cyclic=False), laws.FREEFORM_SCHEMA)
            s1 = _safe_judge(x1["answer"]["expression"], rows)
            entry = {"round1": {"exchange": x1, "scored": s1}}
            if "error" not in s1:
                tree = laws.parse(x1["answer"]["expression"])
                consts = s1["interpolation"]["constants"]
                resid = []
                for a, b in rows[::step][:16]:
                    try:
                        resid.append((a, round(b - laws.evaluate(
                            tree, {"x1": a, **consts}), 5)))
                    except Exception:
                        resid.append((a, None))
                rtable = "\n".join(f"  x1={a}   residual={b}" for a, b in resid)
                x2 = _ask(
                    "You proposed  x2 = " + x1["answer"]["expression"] +
                    f"  for measured data, with fitted constants {consts}. "
                    "Below are the residuals (measured minus predicted). Decide "
                    "whether they are measurement noise or a systematic "
                    "pattern.\n\n" + rtable + "\n\n"
                    "If they are noise, return EXACTLY the same expression "
                    "unchanged — do not invent structure that is not there. If "
                    "they are systematic, refine the law. Same grammar: numbers, "
                    "x1, free constants c1..c4 (fitted for you), pi, + - * / "
                    "parentheses, cos sin exp log sqrt abs pow(base, exponent). "
                    "Then say what physical system, if any, you believe produced "
                    "this data, and one sentence of rationale.",
                    laws.FREEFORM_SCHEMA)
                changed = x2["answer"]["expression"].replace(" ", "") != \
                    x1["answer"]["expression"].replace(" ", "")
                entry["round2"] = {"exchange": x2, "changed": changed,
                                   "scored": _safe_judge(
                                       x2["answer"]["expression"], rows)}
            rec[arm] = entry
            time.sleep(1)
        return rec
    return _checkpointed("b4-secondlaw", rep, run)


# ------------------------------------------------------------------ A: evolution

def arm_a(rep: int) -> bool:
    def run():
        from metascience.auditor import audit_promotion
        from metascience.evolution import (evaluate_detailed, evaluate_strategy,
                                           held_out_seeds, run_generation)
        from metascience.gemini import TUNABLE, GeminiProposer
        from metascience.ledger import FileLedger, PromotionGate
        from metascience.strategy import Strategy

        seeds = held_out_seeds(24)
        ledger = FileLedger(str(ROOT / "runs"))
        gate = PromotionGate(
            ledger, evaluate_strategy, margin=0.02, detailed=evaluate_detailed,
            auditor=lambda r: audit_promotion(
                r, {k: t.__name__ for k, t in TUNABLE.items()}))
        proposer = GeminiProposer()
        champion = Strategy()
        notes = ("accuracy is saturated on most worlds; the strategy spends "
                 "12 experiments x 400 samples each")
        gens = []
        for _ in range(3):
            champion, r = run_generation(ledger, gate, champion, proposer,
                                         seeds, notes)
            gens.append({
                "verdict": r.verdict, "candidate": r.candidate,
                "diff": {k: list(v) for k, v in r.diff.items()},
                "champion_score": r.champion_score,
                "challenger_score": r.challenger_score,
                "gain": round(r.challenger_score - r.champion_score, 5),
                "reason": r.reason,
                "audit": r.audit, "digest": r.digest(),
            })
            notes = (f"{r.candidate} scored {r.challenger_score:+.4f} against "
                     f"champion {r.champion_score:+.4f}. Verdict {r.verdict}.")
        return {"generations": gens,
                "canon": ledger.canon().get("strategy", {}).get("name",
                                                                "champion-v1")}
    return _checkpointed("a-evolution", rep, run)


# ------------------------------------------------------------------------ driver

ARMS = {"b1": arm_b1, "b2": arm_b2, "b3": arm_b3, "b4": arm_b4, "a": arm_a}

ap = argparse.ArgumentParser()
ap.add_argument("--arms", default="b1,b2,b3,b4,a")
ap.add_argument("--reps", type=int, default=REPS)
args = ap.parse_args()

t_start = time.time()
for arm_name in args.arms.split(","):
    fn = ARMS[arm_name.strip()]
    for rep in range(args.reps):
        try:
            ran = fn(rep)
        except Exception as exc:  # noqa: BLE001 — a rep must not kill the campaign
            print(f"[{arm_name} rep {rep:02d}] FAILED: {type(exc).__name__}: "
                  f"{str(exc)[:140]}", flush=True)
            time.sleep(10)
            continue
        state = "done" if ran else "skip (exists)"
        print(f"[{arm_name} rep {rep:02d}] {state}  "
              f"t+{int(time.time() - t_start)}s", flush=True)
        if ran:
            time.sleep(1.5)
print("campaign complete")
