"""Firestore backing for the promotion gate.

Same `Ledger` protocol as the filesystem implementation, so the gate is untouched by
which one is in use — that was the point of writing the gate against an interface.

Tiers are collections, and a record's collection *is* its status. Nothing carries a
status field that could disagree with where it lives, which is the same discipline the
vault uses and for the same reason: one fact, one place.
"""
from __future__ import annotations

import os
from dataclasses import asdict

from google.cloud import firestore

from .ledger import Receipt

RAW, WIKI, RECEIPTS, EXPERIMENTS = "raw", "wiki", "receipts", "experiments"


class FirestoreLedger:
    def __init__(self, project: str | None = None, namespace: str = "metascience"):
        self._db = firestore.Client(project=project or os.environ.get("GEMINI_PROJECT"))
        self._ns = self._db.collection("runs").document(namespace)

    def _col(self, tier: str):
        return self._ns.collection(tier)

    def put_raw(self, key: str, record: dict) -> None:
        self._col(RAW).document(key).set(record)

    def canon(self) -> dict:
        return {d.id: d.to_dict() for d in self._col(WIKI).stream()}

    def set_canon(self, key: str, record: dict) -> None:
        self._col(WIKI).document(key).set(record)

    def put_receipt(self, receipt: Receipt) -> None:
        doc = asdict(receipt) | {"digest": receipt.digest()}
        name = f"{int(receipt.created_at * 1000)}-{receipt.candidate}-{receipt.verdict}"
        self._col(RECEIPTS).document(name).set(doc)

    def receipts(self) -> list[dict]:
        return [d.to_dict() for d in self._col(RECEIPTS).order_by("created_at").stream()]

    def put_experiment(self, record: dict) -> None:
        self._col(EXPERIMENTS).document(record["run_id"]).set(record)

    def experiments(self, limit: int = 500) -> list[dict]:
        q = self._col(EXPERIMENTS).order_by("created_at").limit(limit)
        return [d.to_dict() for d in q.stream()]
