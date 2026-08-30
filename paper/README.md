# The article

LNCS-format draft for a Springer Computer Science Proceedings venue, following
the author guidelines (abstract 70–150 words, middot keywords, two numbered
heading levels, captions above tables and below figures, numbered equations
without section counters, square-bracket citations, Springer reference style,
American English).

Built by CI (`.github/workflows/paper.yml`) — `llncs.cls` is fetched from CTAN
at build time rather than committed, since Springer's class is not ours to
redistribute inside a GPL repository. No local TeX toolchain is required or
expected.

Every number in the draft traces to a committed record: `docs/kepler-test.md`,
`docs/secondlaw/`, `docs/kepler/*.json`, and the fixtures under
`tests/fixtures/`. The bibliography entries are standard works but must be
verified against their actual editions before submission (marked in the
source).

Status: complete skeleton with real prose and real numbers; blocked on the
known gaps before submission anywhere serious — n=1 per live arm, a single
model family, and no symbolic-regression baselines. See "Limitations" in the
draft, which says the same thing to the reviewers.
