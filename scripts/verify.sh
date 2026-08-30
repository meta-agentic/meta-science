#!/usr/bin/env bash
# Everything that must hold before this is submittable.
#
# Run from the repo root. Needs no API key: the anonymisation suite and the whole
# promotion gate are offline by design, so the governance claim is checkable by anyone.
set -uo pipefail
cd "$(dirname "$0")/.."

pass=0; fail=0
check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then printf '  PASS  %s\n' "$desc"; pass=$((pass+1))
  else printf '  FAIL  %s\n' "$desc"; fail=$((fail+1)); fi
}

echo "=== meta-science verification ==="
check "offline test suite"              python3 -m pytest -q
check "the gate still refuses something" bash -c 'python3 run_evolution.py --offline | grep -q REFUSED'
check "the gate still promotes something" bash -c 'python3 run_evolution.py --offline | grep -q PROMOTED'
check "demo runs end to end"            bash -c 'python3 demo.py > /dev/null'
check "worlds reproduce across processes" python3 -m pytest tests/test_worlds.py -q -k FRESH_PROCESS
check "terraform validates"             bash -c 'cd infra && terraform validate'
check "terraform is formatted"          bash -c 'cd infra && terraform fmt -check'
check "no secrets tracked by git"       bash -c '! git ls-files | grep -qE "^\.env$|tfvars$"'
# Agent tooling writes a policy store wherever it is run from, subdirectories
# included, and that store carries machine identity. Two copies reached this repo
# before anyone noticed, so it is checked rather than remembered.
check "no agent tooling tracked"        bash -c '! git ls-files | grep -qE "claude-flow|\.swarm|agentic-qe|ruvnet"'

printf '\n  %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
