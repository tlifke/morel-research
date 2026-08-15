from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import record_types, yaml_io
from .sidecars import Sidecars
from .store import Store


class ExportWouldLoseDecisions(ValueError):
    pass


@dataclass
class Config:
    source: Path
    db: Path
    record_type: str
    reviewer: str
    export_path: Path
    pairs_path: Path | None = None
    footprint_path: Path | None = None

    @property
    def queue_id(self) -> str:
        return str(self.source.resolve())


class Service:
    def __init__(self, config: Config):
        self.config = config
        self.rt = record_types.get(config.record_type)
        self.sidecars = Sidecars(config.pairs_path, config.footprint_path)
        self.last_sync: dict[str, Any] = {}
        self.store = Store(config.db)
        self.store.upsert_queue(
            config.queue_id, self.rt.name, str(config.source.resolve())
        )

    def sync_from_disk(self) -> dict[str, Any]:
        records = [
            yaml_io.normalize_review(r, self.rt)
            for r in yaml_io.load_records(self.config.source)
        ]
        report: dict[str, Any] = dict(
            self.store.import_records(self.config.queue_id, records, self.rt.id_key)
        )
        report.update(self._adopt_file_reviews(records))
        self.last_sync = report
        return report

    def _adopt_file_reviews(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        stored = {
            row["record_id"]: row
            for row in self.store.records(self.config.queue_id)
        }
        adopted: list[str] = []
        kept: list[str] = []
        conflicts: list[dict[str, Any]] = []
        for ordinal, record in enumerate(records):
            record_id = str(record.get(self.rt.id_key) or f"__{ordinal:04d}")
            block = record.get(self.rt.review_key)
            if not isinstance(block, dict):
                continue
            decision = block.get("decision")
            if not decision or decision not in self.rt.decision_names():
                continue
            row = stored.get(record_id)
            if row is None:
                continue
            if row["review"]:
                kept.append(record_id)
                if row["review"]["decision"] != decision:
                    conflicts.append({
                        "record_id": record_id,
                        "kept_from_db": row["review"]["decision"],
                        "ignored_from_file": decision,
                    })
                continue
            edits: dict[str, Any] = {}
            source = copy.deepcopy(record)
            prior = block.get(self.rt.edited_from_key)
            if decision == self.rt.edit_decision and isinstance(prior, dict):
                for key, was in prior.items():
                    if key in self.rt.editable_keys():
                        edits[key] = record_types.dotted(record, key)
                        record_types.set_dotted(source, key, was)
            edited_from = (
                json.dumps(self._edited_from(source, edits), sort_keys=True)
                if edits
                else None
            )
            self.store.save_review(
                self.config.queue_id,
                record_id,
                decision,
                block.get("rationale") or "",
                block.get("reviewer") or self.config.reviewer,
                edits,
                edited_from,
                review_date=block.get("date"),
                origin="import",
                source=source if edits else None,
            )
            adopted.append(record_id)
        return {
            "adopted_from_file": adopted,
            "kept_from_db": kept,
            "conflicts": conflicts,
        }

    def state(self) -> dict[str, Any]:
        rows = self.store.records(self.config.queue_id)
        for row in rows:
            row["merged"] = yaml_io.build_export_record(
                row["source"], row["edits"], None, self.rt
            )
            if row["review"]:
                row["review"]["edited_from"] = (
                    self._edited_from(row["source"], row["edits"])
                    if row["review"]["decision"] == self.rt.edit_decision
                    else None
                )
        return {
            "queue_id": self.config.queue_id,
            "source": str(self.config.source),
            "export_path": str(self.config.export_path),
            "reviewer": self.config.reviewer,
            "schema": self.rt.as_json(),
            "sidecars": self.sidecars.payload(),
            "sidecar_paths": self.sidecars.paths(),
            "last_sync": self.last_sync,
            "db": str(self.config.db),
            "records": rows,
        }

    def save_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        record_id = payload["record_id"]
        decision = payload["decision"]
        rationale = (payload.get("rationale") or "").strip()
        if decision not in self.rt.decision_names():
            raise ValueError(f"unknown decision {decision!r}")
        if self.rt.required_rationale and not rationale:
            raise ValueError("rationale is required on every decision")
        edits = {
            k: v
            for k, v in (payload.get("edits") or {}).items()
            if k in self.rt.editable_keys()
        }
        row = self._row(record_id)
        edited_from = None
        if decision != self.rt.edit_decision:
            edits = {}
        else:
            edits = {k: v for k, v in edits.items()
                     if v != record_types.dotted(row["source"], k)}
            if not edits:
                raise ValueError(
                    f"decision {decision!r} requires at least one changed field"
                )
            edited_from = json.dumps(
                self._edited_from(row["source"], edits), sort_keys=True
            )
        self.store.save_review(
            self.config.queue_id,
            record_id,
            decision,
            rationale,
            payload.get("reviewer") or self.config.reviewer,
            edits,
            edited_from,
        )
        return {"ok": True, "record_id": record_id}

    def save_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.store.save_draft(
            self.config.queue_id,
            payload["record_id"],
            {
                "rationale": payload.get("rationale") or "",
                "decision": payload.get("decision"),
                "edits": payload.get("edits") or {},
            },
        )
        return {"ok": True}

    def _edited_from(
        self, source: dict[str, Any], edits: dict[str, Any]
    ) -> dict[str, Any] | None:
        prior = {
            key: record_types.dotted(source, key)
            for key in self.rt.editable_keys()
            if key in edits
            and edits[key] != record_types.dotted(source, key)
        }
        return prior or None

    def export_records(self) -> list[dict[str, Any]]:
        out = []
        for row in self.store.records(self.config.queue_id):
            review = None
            if row["review"]:
                edited_from = None
                if row["review"]["decision"] == self.rt.edit_decision:
                    edited_from = self._edited_from(row["source"], row["edits"])
                review = {
                    "decision": row["review"]["decision"],
                    "reviewer": row["review"]["reviewer"],
                    "date": row["review"]["date"],
                    "rationale": row["review"]["rationale"],
                    "edited_from": edited_from,
                }
            out.append(
                yaml_io.build_export_record(row["source"], row["edits"], review, self.rt)
            )
        return out

    def _n_decided(self, records: list[dict[str, Any]]) -> int:
        n = 0
        for record in records:
            block = record.get(self.rt.review_key)
            if isinstance(block, dict) and block.get("decision"):
                n += 1
        return n

    def export(
        self, path: str | None = None, force: bool = False
    ) -> dict[str, Any]:
        target = Path(path) if path else self.config.export_path
        target.parent.mkdir(parents=True, exist_ok=True)
        records = self.export_records()
        if target.exists() and not force:
            try:
                existing = yaml_io.load_records(target)
            except (yaml_io.ImportError_, OSError, ValueError):
                existing = None
            if existing is not None:
                had = self._n_decided(existing)
                now = self._n_decided(records)
                if had > now:
                    raise ExportWouldLoseDecisions(
                        f"refusing to export: {target} already holds {had} decided "
                        f"records and this queue has only {now}. Nothing was "
                        f"written. If the queue is empty because its decisions were "
                        f"never loaded, relaunch against {target} so they are "
                        f"adopted, then export. To overwrite anyway, export with "
                        f"force."
                    )
        target.write_text(yaml_io.dump_yaml(records, self.rt), encoding="utf-8")
        counts: dict[str, int] = {name: 0 for name in self.rt.decision_names()}
        counts["unreviewed"] = 0
        for record in records:
            block = record.get(self.rt.review_key) or {}
            key = block.get("decision") or "unreviewed"
            counts[key] = counts.get(key, 0) + 1
        return {"path": str(target.resolve()), "n": len(records), "counts": counts}

    def history(self, record_id: str) -> list[dict[str, Any]]:
        return self.store.history(self.config.queue_id, record_id)

    def _row(self, record_id: str) -> dict[str, Any]:
        for row in self.store.records(self.config.queue_id):
            if row["record_id"] == record_id:
                return row
        raise KeyError(f"no record {record_id!r} in queue")
