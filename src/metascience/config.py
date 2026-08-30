"""Environment loading. Keys come from a gitignored .env and are never logged."""
from __future__ import annotations

import os
from pathlib import Path

# 3.5 is the floor the contest requires. The cascade tries newest first and degrades:
# 3.7-flash returned 503 UNAVAILABLE under load during development, and a benchmark
# that dies because one model is busy is not a benchmark. Every entry is >= 3.5.
MODEL_CASCADE = ("gemini-3.6-flash", "gemini-3.5-flash")
DEFAULT_MODEL = MODEL_CASCADE[0]


def load_env(path: str | Path = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key() -> str:
    load_env()
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing — add it to .env (append with >>)")
    return key


def model_name() -> str:
    return os.environ.get("METASCIENCE_MODEL", DEFAULT_MODEL)
