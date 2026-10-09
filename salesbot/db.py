"""SQLite storage: leads, the append-only Claude transcript per lead, scheduled jobs."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,             -- whatsapp | instagram | email | webchat | phone
    channel_user_id TEXT NOT NULL,     -- phone number, IG scoped id, email address, web session id
    name TEXT, phone TEXT, email TEXT, language TEXT,
    event_type TEXT, event_date TEXT, venue TEXT, emirate TEXT,
    guest_count INTEGER, indoor_outdoor TEXT, services TEXT, budget_aed INTEGER, notes TEXT,
    stage TEXT NOT NULL DEFAULT 'new',
    quote_min_aed INTEGER, quote_max_aed INTEGER,
    marketing_opt_in INTEGER NOT NULL DEFAULT 0,
    do_not_contact INTEGER NOT NULL DEFAULT 0,
    source TEXT,
    agent_notes TEXT,                  -- events the agent must hear about on its next turn
    last_inbound_at REAL, last_outbound_at REAL,
    created_at REAL NOT NULL, updated_at REAL NOT NULL,
    UNIQUE(channel, channel_user_id)
);
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    role TEXT NOT NULL,                -- user | assistant | system
    content TEXT NOT NULL,             -- JSON, exactly as sent to / returned by the API
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS turns_lead ON turns(lead_id, id);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    channel TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    kind TEXT NOT NULL,                -- followup | review_request | reactivation | daily_digest
    payload TEXT NOT NULL DEFAULT '{}',
    run_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | done | cancelled | failed
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_due ON jobs(status, run_at);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    kind TEXT NOT NULL, preferred_time TEXT NOT NULL, notes TEXT,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS seen_messages (
    message_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL
);
"""

LEAD_FIELDS = (
    "name", "phone", "email", "language", "event_type", "event_date", "venue", "emirate",
    "guest_count", "indoor_outdoor", "services", "budget_aed", "notes", "stage",
    "quote_min_aed", "quote_max_aed", "marketing_opt_in", "do_not_contact", "source",
    "agent_notes", "last_inbound_at", "last_outbound_at",
)


class Database:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # Leads

    def get_or_create_lead(self, channel: str, channel_user_id: str, **fields: Any) -> dict:
        row = self.conn.execute(
            "SELECT * FROM leads WHERE channel = ? AND channel_user_id = ?", (channel, channel_user_id)
        ).fetchone()
        if row:
            return dict(row)
        now = time.time()
        self.conn.execute(
            "INSERT INTO leads (channel, channel_user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (channel, channel_user_id, now, now),
        )
        self.conn.commit()
        lead = self.conn.execute(
            "SELECT * FROM leads WHERE channel = ? AND channel_user_id = ?", (channel, channel_user_id)
        ).fetchone()
        if fields:
            self.update_lead(lead["id"], **fields)
        return self.get_lead(lead["id"])

    def get_lead(self, lead_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if row is None:
            raise KeyError(f"lead {lead_id} not found")
        return dict(row)

    def update_lead(self, lead_id: int, **fields: Any) -> dict:
        updates = {k: v for k, v in fields.items() if k in LEAD_FIELDS and v is not None}
        if updates:
            assignments = ", ".join(f"{k} = ?" for k in updates)
            self.conn.execute(
                f"UPDATE leads SET {assignments}, updated_at = ? WHERE id = ?",
                (*updates.values(), time.time(), lead_id),
            )
            self.conn.commit()
        return self.get_lead(lead_id)

    def list_leads(self, limit: int = 200) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM leads ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    # Transcript (append-only: never edit or delete rows, or Claude's thinking replay breaks)

    def append_turn(self, lead_id: int, role: str, content: Any) -> None:
        self.conn.execute(
            "INSERT INTO turns (lead_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (lead_id, role, json.dumps(content, ensure_ascii=False), time.time()),
        )
        self.conn.commit()

    def transcript(self, lead_id: int) -> list[dict]:
        rows = self.conn.execute("SELECT role, content FROM turns WHERE lead_id = ? ORDER BY id", (lead_id,))
        return [{"role": r["role"], "content": json.loads(r["content"])} for r in rows]

    def last_turn_id(self, lead_id: int) -> int:
        row = self.conn.execute("SELECT MAX(id) FROM turns WHERE lead_id = ?", (lead_id,)).fetchone()
        return row[0] or 0

    def rollback_turns(self, lead_id: int, after_id: int) -> None:
        """Drop the turns of a failed run. Only ever removes the tail, so no earlier turn changes."""
        self.conn.execute("DELETE FROM turns WHERE lead_id = ? AND id > ?", (lead_id, after_id))
        self.conn.commit()

    # Outbox: every message actually sent to the customer, for the dashboard and web chat

    def record_outbound(self, lead_id: int, channel: str, text: str) -> None:
        now = time.time()
        self.conn.execute(
            "INSERT INTO outbox (lead_id, channel, text, created_at) VALUES (?, ?, ?, ?)",
            (lead_id, channel, text, now),
        )
        self.conn.execute("UPDATE leads SET last_outbound_at = ?, updated_at = ? WHERE id = ?", (now, now, lead_id))
        self.conn.commit()

    def outbound_messages(self, lead_id: int) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM outbox WHERE lead_id = ? ORDER BY id", (lead_id,))
        return [dict(r) for r in rows]

    # Jobs

    def schedule_job(self, kind: str, run_at: float, lead_id: int | None = None, payload: dict | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO jobs (lead_id, kind, payload, run_at, created_at) VALUES (?, ?, ?, ?, ?)",
            (lead_id, kind, json.dumps(payload or {}), run_at, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid

    def cancel_jobs(self, lead_id: int, kinds: tuple[str, ...]) -> None:
        marks = ",".join("?" for _ in kinds)
        self.conn.execute(
            f"UPDATE jobs SET status = 'cancelled' WHERE lead_id = ? AND status = 'pending' AND kind IN ({marks})",
            (lead_id, *kinds),
        )
        self.conn.commit()

    def due_jobs(self, now: float) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'pending' AND run_at <= ? ORDER BY run_at", (now,)
        ).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def pending_jobs(self, lead_id: int | None = None, kind: str | None = None) -> list[dict]:
        sql, args = "SELECT * FROM jobs WHERE status = 'pending'", []
        if lead_id is not None:
            sql, args = sql + " AND lead_id = ?", [*args, lead_id]
        if kind is not None:
            sql, args = sql + " AND kind = ?", [*args, kind]
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in self.conn.execute(sql, args)]

    def finish_job(self, job_id: int, status: str = "done") -> None:
        self.conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        self.conn.commit()

    def reschedule_job(self, job_id: int, run_at: float) -> None:
        self.conn.execute("UPDATE jobs SET run_at = ? WHERE id = ?", (run_at, job_id))
        self.conn.commit()

    # Bookings

    def add_booking(self, lead_id: int, kind: str, preferred_time: str, notes: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO bookings (lead_id, kind, preferred_time, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (lead_id, kind, preferred_time, notes, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid

    def bookings(self, lead_id: int) -> list[dict]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM bookings WHERE lead_id = ?", (lead_id,))]

    # Webhook de-duplication (Meta retries deliveries)

    def mark_seen(self, message_id: str) -> bool:
        """Return True the first time a message id is seen, False on a repeat delivery."""
        try:
            self.conn.execute("INSERT INTO seen_messages (message_id, created_at) VALUES (?, ?)", (message_id, time.time()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
