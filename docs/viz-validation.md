# Evidence page — validation verdict

Produced by `scripts/validate_viz.py`: the rationale and the actual figure
data were given to an independent Gemini reviewer with an adversarial brief.
Recorded verbatim, whichever way it landed.

**Verdict: SOUND**

- **Strongest objection**: The primary potential critique is the exclusion of three arms from Figure 1, which could be misconstrued as cherry-picking if the rationale were not explicitly clear about the measurement-efficiency scope and the worst-case arm (blunt) being reported in Figure 2's tables.
- **Misleading risk**: Low. The design strictly adheres to perceptual accuracy guidelines: common aligned scales, zero baselines, jittered point distributions to reveal variance rather than hiding it in means, and color paired redundantly with direct labels.

| figure | encoding | reasoning | severity | concern |
|---|---|---|---|---|
| 1 | ok | holds | none | Excludes 3 of 8 strategy arms from the plot, but this is explicitly disclosed and justified in the rationale as focusing on the core measurement-efficiency by noise-regime contrast while avoiding clutter, with full data available in accompanying tables. |
| 2 | ok | holds | none | None. Sorting nominal categories by refutation rate on a common horizontal scale with direct count labels and zero baseline follows visual hierarchy best practices. |
| 3 | ok | holds | none | The text headline '5 of 6 priors inverted' approximates the 94/112 (83.9%) exact empirical split, but the bar itself correctly displays exact percentages and raw counts (94 vs 18). |
| 4 | ok | holds | none | None. Presenting raw true/false outcome counts in horizontal stacked bars alongside precision/recall text annotations avoids misleading matrix constructs and maintains accurate zero-based length encodings. |
