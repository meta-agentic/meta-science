"""Aggregate the repetition campaign and draw the papers' figures.

Reads runs/campaign/*/rep-*.json, writes docs/campaign/summary.json and
vector figures (PDF for LaTeX, PNG preview) into docs/campaign/figures/.
Figures follow the LNCS guidance: vector, legible in black and white, no
lettering below 6pt.
"""
import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAMP = ROOT / "runs" / "campaign"
OUT = ROOT / "docs" / "campaign"
FIGS = OUT / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 9, "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False})

INK = "#222222"
BLUE = "#2a78d6"
ORANGE = "#eb6834"


def reps(arm: str):
    return [json.loads(p.read_text())
            for p in sorted((CAMP / arm).glob("rep-*.json"))]


def wilson(k: int, n: int):
    """95% Wilson interval for a proportion."""
    if n == 0:
        return 0.0, 0.0, 0.0
    z = 1.96
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


summary = {}

# ------------------------------------------------------------------- B1: recall
b1 = reps("b1-recall")
if b1:
    rec = {}
    for arm in ("tycho_blind", "tycho_labeled", "synth_blind"):
        n = len(b1)
        k = sum(1 for r in b1 if r[arm]["recognises"])
        errs = sorted(r[arm]["scored"].get("interpolation", {})
                      .get("holdout_mean_abs_err") or math.inf for r in b1)
        rec[arm] = {"n": n, "recognises": k, "rate": wilson(k, n),
                    "median_err": errs[n // 2]}
    summary["b1_recall"] = rec

    fig, ax = plt.subplots(figsize=(3.6, 2.4))
    arms = ["tycho_blind", "tycho_labeled", "synth_blind"]
    labels = ["Tycho\nblind", "Tycho\nlabeled", "synthetic\nblind"]
    ps = [rec[a]["rate"][0] for a in arms]
    los = [rec[a]["rate"][0] - rec[a]["rate"][1] for a in arms]
    his = [rec[a]["rate"][2] - rec[a]["rate"][0] for a in arms]
    ax.bar(labels, ps, yerr=[los, his], capsize=4,
           color=["white", BLUE, "white"], edgecolor=INK, linewidth=1)
    ax.set_ylabel("recognition rate")
    ax.set_ylim(0, 1.05)
    for i, a in enumerate(arms):
        ax.text(i, 0.02, f"n={rec[a]['n']}", ha="center", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGS / f"recognition-rate.{ext}")
    plt.close(fig)

# ---------------------------------------------------------------- B2: refinement
b2 = reps("b2-refine")
if b2:
    pairs = []
    shapes = {"conic": 0, "cosine": 0, "other": 0}
    for r in b2:
        e1 = r["round1"]["exchange"]["answer"]["expression"].replace(" ", "")
        s1 = r["round1"]["scored"]
        if re.search(r"/\(?[^)]*cos", e1):
            shapes["conic"] += 1
        elif "cos" in e1:
            shapes["cosine"] += 1
        else:
            shapes["other"] += 1
        err1 = (s1.get("interpolation") or {}).get("holdout_mean_abs_err")
        if "round2" in r:
            err2 = (r["round2"]["scored"].get("interpolation") or {}) \
                .get("holdout_mean_abs_err")
            pairs.append((err1, err2))
    summary["b2_refine"] = {
        "n": len(b2), "round1_shapes": shapes,
        "round2_ran": len(pairs),
        "round2_improved": sum(1 for a, b in pairs
                               if a and b and b < a),
    }

    if pairs:
        fig, ax = plt.subplots(figsize=(3.2, 2.6))
        for a, b in pairs:
            if a and b:
                ax.plot([0, 1], [a, b], color=INK, alpha=0.35, linewidth=0.8)
                ax.scatter([0, 1], [a, b], s=10,
                           c=[ORANGE, BLUE], zorder=3)
        ax.set_yscale("log")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["round 1", "round 2\n(residual feedback)"])
        ax.set_ylabel("held-out error (log)")
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(FIGS / f"refinement.{ext}")
        plt.close(fig)

# ----------------------------------------------------------------- B3: third law
b3 = reps("b3-thirdlaw")
if b3:
    exponents = []
    named = 0
    for r in b3:
        expr = r["exchange"]["answer"]["expression"].replace(" ", "")
        consts = (r["scored"].get("interpolation") or {}).get("constants", {})
        m = re.search(r"pow\(x1,(c[1-4]|[0-9.]+)\)", expr)
        if m:
            token = m.group(1)
            exponents.append(consts.get(token) if token.startswith("c")
                             else float(token))
        if r["mentions_kepler_or_cl"]:
            named += 1
    exponents = [e for e in exponents if e is not None]
    summary["b3_thirdlaw"] = {
        "n": len(b3), "power_law_form": len(exponents),
        "named_a_3_2_law": named,
        "exponent_mean": (round(sum(exponents) / len(exponents), 4)
                          if exponents else None),
        "exponent_min": min(exponents) if exponents else None,
        "exponent_max": max(exponents) if exponents else None,
    }

    if exponents:
        fig, ax = plt.subplots(figsize=(3.2, 2.2))
        ax.hist(exponents, bins=12, color="white", edgecolor=INK)
        ax.axvline(1.5, color=ORANGE, linewidth=1.2, linestyle="--")
        ax.text(1.5, ax.get_ylim()[1] * 0.9, " 3/2", color=ORANGE, fontsize=8)
        ax.set_xlabel("fitted exponent of the proposed law")
        ax.set_ylabel("repetitions")
        fig.tight_layout()
        for ext in ("pdf", "png"):
            fig.savefig(FIGS / f"thirdlaw-exponent.{ext}")
        plt.close(fig)

# ---------------------------------------------------------------- B4: second law
b4 = reps("b4-secondlaw")
if b4:
    rec = {}
    for arm in ("equal_areas", "drag"):
        n = kept = final_ok = 0
        for r in b4:
            if arm not in r:
                continue
            n += 1
            entry = r[arm]
            final = entry.get("round2", entry["round1"])
            if entry.get("round2", {}).get("changed") is False:
                kept += 1
            if final["scored"].get("extrapolates"):
                final_ok += 1
        rec[arm] = {"n": n, "kept_in_round2": kept,
                    "final_extrapolates": final_ok}
    summary["b4_secondlaw"] = rec

# ------------------------------------------------------------------ A: evolution
a = reps("a-evolution")
if a:
    patterns = {}
    gains = {1: [], 2: [], 3: []}
    promoted_gains = []
    refused_higher = refused_lower = 0
    audit = {"flagged": 0, "legitimate": 0, "other": 0}
    knob_changed = 0
    for r in a:
        gens = r["generations"]
        pat = "".join(g["verdict"][0] for g in gens)
        patterns[pat] = patterns.get(pat, 0) + 1
        for i, g in enumerate(gens):
            gains[i + 1].append(g["gain"])
            if g["verdict"] == "PROMOTED":
                promoted_gains.append(g["gain"])
                aud = g.get("audit") or {}
                verdict = aud.get("legitimate")
                audit["flagged" if verdict is False else
                      "legitimate" if verdict is True else "other"] += 1
            else:
                if g["gain"] > 0:
                    refused_higher += 1
                else:
                    refused_lower += 1
        if any("samples_per_arm" not in g["diff"] for g in gens):
            knob_changed += 1
    summary["a_evolution"] = {
        "n": len(a), "verdict_patterns": patterns,
        "refused_higher_scoring": refused_higher,
        "refused_lower_scoring": refused_lower,
        "audit_on_promotions": audit,
        "changed_knob_at_least_once": knob_changed,
    }

    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    for gen in (1, 2, 3):
        xs = [gen + (i - len(gains[gen]) / 2) * 0.012
              for i in range(len(gains[gen]))]
        promoted = [g >= 0.02 for g in gains[gen]]
        ax.scatter(xs, gains[gen], s=12,
                   c=[BLUE if p else ORANGE for p in promoted],
                   edgecolors=INK, linewidths=0.3, zorder=3)
    ax.axhline(0.02, color=INK, linewidth=1, linestyle="--")
    ax.text(3.25, 0.021, "margin $\\varepsilon$", fontsize=8)
    ax.axhline(0.0, color=INK, linewidth=0.5, alpha=0.4)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels(["gen 1", "gen 2", "gen 3"])
    ax.set_ylabel("challenger gain over champion")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIGS / f"evolution-gains.{ext}")
    plt.close(fig)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
print(f"\nfigures in {FIGS}")
