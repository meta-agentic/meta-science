# Paper A — the meta-science system paper

LNCS-format draft: *Meta-Science: Falsifiable Scientific Reasoning by Agents on
Anonymized Causal Worlds*. This is the foundation half of a deliberate
two-paper plan:

- **Paper A (this branch, `paper-metascience`)** — the system: anonymized
  causal worlds, discovery by refutation, the promotion gate with margins,
  receipts, and the advisory auditor. Evidence: the 384-run study, the 0/4 vs
  4/4 measurement, and the three published live runs in `docs/receipts/`.
- **Paper B (branch `paper-instrument`)** — the instrument: recall versus
  inference in law induction (the Kepler line: Tycho, synthetic planets,
  law-breaking worlds, the time-split judge).

Rule of the pair, stated in both papers: **no result is reported in both.**
Each cites the other as companion.

Built by CI only (`.github/workflows/paper.yml`); `llncs.cls` is fetched from
CTAN at build time, never committed. Every number traces to a committed
artifact: `static/study.json`, `docs/receipts/`, `README.md`'s pinned tables,
and the tests that fail if prose and code drift apart. Bibliography entries
must be verified against actual editions before submission (marked in source).

Blocking gaps before submission, same as the companion's: a repetition
campaign (live evidence is three runs), a second model family, and — for this
paper — richer world mechanisms, since the current ones are kind enough that
replication is cost-neutral.
