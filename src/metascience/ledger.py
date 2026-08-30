"""raw → wiki → output, with promotion as a gated transition.

The invariant this file exists to enforce:

    An agent never promotes its own output to canon — including its own improvements.

`put_raw` is unrestricted: anything may be *proposed*. `promote` is the only path to
canon, it runs the evidence itself rather than accepting a claimed score, and it writes
a receipt whichever way it goes. A refusal is as much a record as a promotion — a gate
that only logs its successes proves nothing.

`Ledger` is a protocol so the Firestore backing swaps in without touching the gate.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Protocol

PROMOTED, REFUSED = "PROMOTED", "REFUSED"


@dataclass
class Receipt:
    """Everything needed to re-derive the verdict independently."""
    verdict: str
    candidate: str
    parent: str | None
    diff: dict
    champion_score: float
    challenger_score: float
    margin_required: float
    world_seeds: list[int]
    reason: str
    created_at: float
    # Kept apart so a reader — human or model — can see whether accuracy survived the
    # change or was merely outrun by the cost saving.
    champion_parts: dict | None = None
    challenger_parts: dict | None = None
    audit: dict | None = None

    def digest(self) -> str:
        body = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(body).hexdigest()[:16]


class Ledger(Protocol):
    def put_raw(self, key: str, record: dict) -> None: ...
    def canon(self) -> dict: ...
    def set_canon(self, key: str, record: dict) -> None: ...
    def put_receipt(self, receipt: Receipt) -> None: ...


class FileLedger:
    """Filesystem implementation. Tiers are directories, exactly as the vault does it —
    the tier a record sits in *is* its status, so the two cannot disagree."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        for tier in ("raw", "wiki", "output", "receipts"):
            (self.root / tier).mkdir(parents=True, exist_ok=True)

    def put_raw(self, key: str, record: dict) -> None:
        (self.root / "raw" / f"{key}.json").write_text(json.dumps(record, indent=2))

    def canon(self) -> dict:
        out = {}
        for f in sorted((self.root / "wiki").glob("*.json")):
            out[f.stem] = json.loads(f.read_text())
        return out

    def set_canon(self, key: str, record: dict) -> None:
        (self.root / "wiki" / f"{key}.json").write_text(json.dumps(record, indent=2))

    def put_receipt(self, receipt: Receipt) -> None:
        name = f"{int(receipt.created_at * 1000)}-{receipt.candidate}-{receipt.verdict}"
        (self.root / "receipts" / f"{name}.json").write_text(
            json.dumps(asdict(receipt) | {"digest": receipt.digest()}, indent=2))

    def receipts(self) -> list[dict]:
        return [json.loads(f.read_text())
                for f in sorted((self.root / "receipts").glob("*.json"))]


class PromotionGate:
    """Runs the evidence itself. The proposer supplies a candidate and nothing else —
    no score, no benchmark access, no say in the verdict."""

    def __init__(self, ledger: Ledger, evaluate: Callable[[object, list[int]], float],
                 margin: float = 0.02, detailed=None, auditor=None):
        self._ledger = ledger
        self._evaluate = evaluate
        self._detailed = detailed          # optional: score with its parts separated
        self._auditor = auditor            # optional: advisory only, never a veto
        self.margin = margin

    def consider(self, champion, challenger, world_seeds: list[int]) -> Receipt:
        # Both arms run on the same held-out worlds under the same seeds. The proposer
        # never sees these seeds, so it cannot tune against them.
        if self._detailed:
            champ_parts = self._detailed(champion, world_seeds)
            chal_parts = self._detailed(challenger, world_seeds)
            champ_score, chal_score = champ_parts["score"], chal_parts["score"]
        else:
            champ_parts = chal_parts = None
            champ_score = self._evaluate(champion, world_seeds)
            chal_score = self._evaluate(challenger, world_seeds)
        wins = chal_score >= champ_score + self.margin

        receipt = Receipt(
            verdict=PROMOTED if wins else REFUSED,
            candidate=challenger.name,
            parent=getattr(challenger, "parent", None),
            diff=challenger.diff(champion) if hasattr(challenger, "diff") else {},
            champion_score=round(champ_score, 4),
            challenger_score=round(chal_score, 4),
            margin_required=self.margin,
            world_seeds=list(world_seeds),
            reason=("beat the champion on held-out worlds by the required margin" if wins
                    else f"gained {chal_score - champ_score:+.4f}, needed +{self.margin}"),
            created_at=time.time(),
            champion_parts=champ_parts,
            challenger_parts=chal_parts,
        )
        # The audit runs after the verdict on purpose. A promotion that turned on a
        # model's opinion would reintroduce exactly what the gate exists to prevent, so
        # the auditor annotates the record and cannot change it.
        if self._auditor and wins:
            receipt.audit = self._auditor(receipt)
        self._ledger.put_receipt(receipt)
        if wins:
            self._ledger.set_canon("strategy", {"name": challenger.name,
                                                "digest": challenger.digest()})
        return receipt
