#!/usr/bin/env python3
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "sadaqahledger.db"
DEFAULT_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "charities_seed.csv"


def seed_database(db_path: Path = DEFAULT_DB_PATH, csv_path: Path = DEFAULT_CSV_PATH) -> int:
    conn = sqlite3.connect(db_path)
    existing = conn.execute("SELECT COUNT(*) FROM charities").fetchone()[0]
    if existing:
        conn.close()
        return existing

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [
            (
                row["name"],
                row["country"],
                row["registration_number"],
                row["website"],
                row["cause"],
                row["verified_at"],
                row["verification_source"],
                int(row["fraud_count"]),
                int(row["is_active"]),
            )
            for row in reader
        ]

    conn.executemany(
        """
        INSERT INTO charities (
            name, country, registration_number, website, cause,
            verified_at, verification_source, fraud_count, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM charities").fetchone()[0]
    conn.close()
    return total


if __name__ == "__main__":
    count = seed_database()
    print(f"Seeded {count} charities")
