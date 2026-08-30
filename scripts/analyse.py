#!/usr/bin/env python3
"""Turn the recorded runs into the tables a paper would carry.

Everything here is arithmetic over stored records — nothing is recomputed by re-running
the agent. So these numbers describe what was observed, and they stay valid against the
data even if the code later changes.

    python3 scripts/collect.py --worlds 48
    python3 scripts/analyse.py
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from metascience.ledger import FileLedger  # noqa: E402


def _arm(rec: dict) -> str:
    return (rec.get("config") or {}).get("strategy", {}).get("name", "?")


def _paired(rec: dict) -> bool:
    return bool((rec.get("config") or {}).get("strategy", {}).get("paired_arms"))


def _samples(rec: dict) -> int:
    return (rec.get("config") or {}).get("strategy", {}).get("samples_per_arm", 0)


def _accuracy(rec: dict) -> list[float]:
    return [t["held_out"]["direction_accuracy"] for t in rec.get("trials", [])
            if (t.get("held_out") or {}).get("direction_accuracy") is not None]


def table(title: str, headers: list[str], rows: list[list]) -> None:
    print(f"\n{title}\n" + "-" * 74)
    widths = [max(len(str(h)), *(len(f"{r[i]}") for r in rows)) for i, h in enumerate(headers)]
    print("  " + "  ".join(f"{h:<{w}}" for h, w in zip(headers, widths)))
    for r in rows:
        print("  " + "  ".join(f"{c:<{w}}" for c, w in zip(r, widths)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="runs/study")
    args = ap.parse_args()
    records = FileLedger(args.data).experiments(limit=100_000)
    if not records:
        sys.exit(f"no records in {args.data} — run scripts/collect.py first")

    print(f"meta-science · analysis over {len(records)} recorded runs")

    # -- 1. Does cutting measurement cost accuracy? Only when the noise is independent.
    by_arm = defaultdict(list)
    for r in records:
        by_arm[_arm(r)] += _accuracy(r)
    rows = []
    for arm in ("champion", "frugal-100", "lean-25", "paired-champion", "paired-lean-25"):
        vals = by_arm.get(arm, [])
        if vals:
            rows.append([arm, len(vals), f"{st.mean(vals):.4f}",
                         f"{st.stdev(vals):.4f}" if len(vals) > 1 else "—"])
    table("1 · Measurement efficiency is real only under independent noise",
          ["arm", "n", "mean accuracy", "sd"], rows)
    print("\n  Paired arms share noise, so accuracy barely moves as samples are cut and the")
    print("  cheapest strategy always wins. Independent arms expose the trade-off.")

    # -- 2. The confounded template: does the agent beat its own observational prior?
    inverted = agreed = 0
    for r in records:
        for t in r.get("trials", []):
            if t.get("template_id") != "T6":
                continue
            for e in t.get("experiments", []):
                if e["predicted_sign"] and e["measured_effect"]:
                    if e["predicted_sign"] * e["measured_effect"] < 0:
                        inverted += 1
                    else:
                        agreed += 1
    total = inverted + agreed
    table("2 · On the confounded template, observation predicts the wrong sign",
          ["outcome", "count", "share"],
          [["prior inverted by experiment", inverted, f"{inverted/total:.3f}" if total else "—"],
           ["prior confirmed", agreed, f"{agreed/total:.3f}" if total else "—"]])

    # -- 3. Refutation rate by template: where is the agent most often wrong?
    ref = defaultdict(lambda: [0, 0])
    for r in records:
        for t in r.get("trials", []):
            tid = t.get("template_id", "?")
            for e in t.get("experiments", []):
                ref[tid][1] += 1
                if e["verdict"] == "REFUTED":
                    ref[tid][0] += 1
    table("3 · Refutation rate by world type",
          ["template", "refuted", "tested", "rate"],
          [[k, v[0], v[1], f"{v[0]/v[1]:.3f}"] for k, v in sorted(ref.items())])

    # -- 4. Does the observational screen help, or just cost experiments?
    rows = []
    for arm in ("champion", "no-screening", "blunt", "sensitive"):
        vals = by_arm.get(arm, [])
        if vals:
            rows.append([arm, len(vals), f"{st.mean(vals):.4f}"])
    table("4 · Effect of the ranking heuristic and the decision threshold",
          ["arm", "n", "mean accuracy"], rows)

    # -- 5. Precision of the recovered edges against ground truth.
    tp = fp = fn = 0
    for r in records:
        if _arm(r) != "champion":
            continue
        for t in r.get("trials", []):
            truth = (t.get("ground_truth") or {}).get("edges", {})
            observable = set(t.get("variables", []))
            real = {(c, e) for e, parents in truth.items() for c in parents
                    if c in observable and e in observable}
            claimed = {tuple(k.split("->")) for k in (t.get("model") or {})}
            tp += len(real & claimed)
            fp += len(claimed - real)
            fn += len(real - claimed)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec_ = tp / (tp + fn) if tp + fn else 0.0
    table("5 · Recovered edges against hidden ground truth (champion arm)",
          ["true pos", "false pos", "false neg", "precision", "recall"],
          [[tp, fp, fn, f"{prec:.3f}", f"{rec_:.3f}"]])
    print("\n  Ground truth is read here and nowhere on the agent's path.\n")


if __name__ == "__main__":
    main()
