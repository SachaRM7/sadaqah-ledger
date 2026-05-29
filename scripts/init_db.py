#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "sadaqahledger.db"


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS charities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            registration_number TEXT NOT NULL,
            website TEXT NOT NULL,
            cause TEXT NOT NULL,
            verified_at TEXT,
            verification_source TEXT,
            fraud_count INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            charity_hash TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            donation_hash TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            email TEXT,
            zakat_due_date TEXT NOT NULL,
            reminder_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fraud_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            charity_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            reported_at TEXT NOT NULL,
            FOREIGN KEY (charity_id) REFERENCES charities(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()
    return db_path


if __name__ == "__main__":
    path = initialize_database()
    print(f"Initialized database at {path}")
