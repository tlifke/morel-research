from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS queues (
    queue_id     TEXT PRIMARY KEY,
    record_type  TEXT NOT NULL,
    source_path  TEXT NOT NULL,
    imported_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS records (
    queue_id     TEXT NOT NULL,
    record_id    TEXT NOT NULL,
    ordinal      INTEGER NOT NULL,
    source_json  TEXT NOT NULL,
    edits_json   TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (queue_id, record_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    queue_id     TEXT NOT NULL,
    record_id    TEXT NOT NULL,
    decision     TEXT NOT NULL,
    rationale    TEXT NOT NULL,
    reviewer     TEXT NOT NULL,
    review_date  TEXT NOT NULL,
    edited_from  TEXT,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (queue_id, record_id)
);

CREATE TABLE IF NOT EXISTS review_history (
    history_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_id     TEXT NOT NULL,
    record_id    TEXT NOT NULL,
    decision     TEXT NOT NULL,
    rationale    TEXT NOT NULL,
    reviewer     TEXT NOT NULL,
    review_date  TEXT NOT NULL,
    edited_from  TEXT,
    edits_json   TEXT NOT NULL DEFAULT '{}',
    written_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    queue_id     TEXT NOT NULL,
    record_id    TEXT NOT NULL,
    draft_json   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (queue_id, record_id)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return date.today().isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.execute("PRAGMA synchronous=FULL")
        self._migrate()
        self.conn.commit()
        self.checkpoint()

    def _migrate(self) -> None:
        columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(review_history)")
        }
        if "origin" not in columns:
            self.conn.execute("ALTER TABLE review_history ADD COLUMN origin TEXT")

    def checkpoint(self) -> None:
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def close(self) -> None:
        self.conn.close()

    def upsert_queue(
        self, queue_id: str, record_type: str, source_path: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO queues (queue_id, record_type, source_path, imported_at) "
            "VALUES (?,?,?,?) ON CONFLICT(queue_id) DO UPDATE SET "
            "record_type=excluded.record_type, source_path=excluded.source_path, "
            "imported_at=excluded.imported_at",
            (queue_id, record_type, source_path, now()),
        )
        self.conn.commit()

    def queue(self, queue_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM queues WHERE queue_id=?", (queue_id,)
        ).fetchone()
        return dict(row) if row else None

    def queues(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM queues ORDER BY imported_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def import_records(
        self, queue_id: str, records: list[dict[str, Any]], id_key: str
    ) -> dict[str, int]:
        added = updated = 0
        for ordinal, record in enumerate(records):
            record_id = str(record.get(id_key) or f"__{ordinal:04d}")
            source_json = json.dumps(record, sort_keys=True)
            existing = self.conn.execute(
                "SELECT source_json FROM records WHERE queue_id=? AND record_id=?",
                (queue_id, record_id),
            ).fetchone()
            if existing is None:
                self.conn.execute(
                    "INSERT INTO records (queue_id, record_id, ordinal, source_json) "
                    "VALUES (?,?,?,?)",
                    (queue_id, record_id, ordinal, source_json),
                )
                added += 1
            else:
                self.conn.execute(
                    "UPDATE records SET ordinal=?, source_json=? "
                    "WHERE queue_id=? AND record_id=?",
                    (ordinal, source_json, queue_id, record_id),
                )
                if existing["source_json"] != source_json:
                    updated += 1
        self.conn.commit()
        return {"added": added, "updated": updated}

    def records(self, queue_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT r.record_id, r.ordinal, r.source_json, r.edits_json, "
            "  v.decision, v.rationale, v.reviewer, v.review_date, v.edited_from, "
            "  v.updated_at, d.draft_json "
            "FROM records r "
            "LEFT JOIN reviews v ON v.queue_id=r.queue_id AND v.record_id=r.record_id "
            "LEFT JOIN drafts d ON d.queue_id=r.queue_id AND d.record_id=r.record_id "
            "WHERE r.queue_id=? ORDER BY r.ordinal",
            (queue_id,),
        ).fetchall()
        out = []
        for row in rows:
            review = None
            if row["decision"]:
                review = {
                    "decision": row["decision"],
                    "rationale": row["rationale"],
                    "reviewer": row["reviewer"],
                    "date": row["review_date"],
                    "edited_from": row["edited_from"],
                    "updated_at": row["updated_at"],
                }
            out.append(
                {
                    "record_id": row["record_id"],
                    "ordinal": row["ordinal"],
                    "source": json.loads(row["source_json"]),
                    "edits": json.loads(row["edits_json"] or "{}"),
                    "review": review,
                    "draft": json.loads(row["draft_json"]) if row["draft_json"] else None,
                }
            )
        return out

    def save_review(
        self,
        queue_id: str,
        record_id: str,
        decision: str,
        rationale: str,
        reviewer: str,
        edits: dict[str, Any],
        edited_from: str | None,
        review_date: str | None = None,
        origin: str = "app",
        source: dict[str, Any] | None = None,
    ) -> None:
        stamp = review_date or today()
        ts = now()
        if source is None:
            self.conn.execute(
                "UPDATE records SET edits_json=? WHERE queue_id=? AND record_id=?",
                (json.dumps(edits, sort_keys=True), queue_id, record_id),
            )
        else:
            self.conn.execute(
                "UPDATE records SET edits_json=?, source_json=? "
                "WHERE queue_id=? AND record_id=?",
                (
                    json.dumps(edits, sort_keys=True),
                    json.dumps(source, sort_keys=True),
                    queue_id,
                    record_id,
                ),
            )
        self.conn.execute(
            "INSERT INTO reviews (queue_id, record_id, decision, rationale, reviewer, "
            "  review_date, edited_from, updated_at) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(queue_id, record_id) DO UPDATE SET decision=excluded.decision, "
            "  rationale=excluded.rationale, reviewer=excluded.reviewer, "
            "  review_date=excluded.review_date, edited_from=excluded.edited_from, "
            "  updated_at=excluded.updated_at",
            (queue_id, record_id, decision, rationale, reviewer, stamp, edited_from, ts),
        )
        self.conn.execute(
            "INSERT INTO review_history (queue_id, record_id, decision, rationale, "
            "  reviewer, review_date, edited_from, edits_json, written_at, origin) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                queue_id,
                record_id,
                decision,
                rationale,
                reviewer,
                stamp,
                edited_from,
                json.dumps(edits, sort_keys=True),
                ts,
                origin,
            ),
        )
        self.conn.execute(
            "DELETE FROM drafts WHERE queue_id=? AND record_id=?", (queue_id, record_id)
        )
        self.conn.commit()
        self.checkpoint()

    def save_draft(self, queue_id: str, record_id: str, draft: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO drafts (queue_id, record_id, draft_json, updated_at) "
            "VALUES (?,?,?,?) ON CONFLICT(queue_id, record_id) DO UPDATE SET "
            "draft_json=excluded.draft_json, updated_at=excluded.updated_at",
            (queue_id, record_id, json.dumps(draft, sort_keys=True), now()),
        )
        self.conn.commit()

    def history(self, queue_id: str, record_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT decision, rationale, reviewer, review_date, edited_from, "
            "  written_at, origin "
            "FROM review_history WHERE queue_id=? AND record_id=? ORDER BY history_id",
            (queue_id, record_id),
        ).fetchall()
        return [dict(r) for r in rows]
