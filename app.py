#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from config import (
    APP_TITLE,
    DATABASE_PATH,
    PRICE_CACHE_HOURS,
    PRICES_CACHE_PATH,
    SECRET_KEY,
    DEFAULT_GOLD_PRICE_PER_GRAM,
    DEFAULT_SILVER_PRICE_PER_GRAM,
)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = SECRET_KEY

GOLD_NISAB_GRAMS = 87.48
SILVER_NISAB_GRAMS = 612.36
VALID_SCHOOLS = {"hanafi", "shafi", "maliki", "hanbali"}
REMINDER_OFFSETS = [30, 7, 0, -7]


@dataclass
class MetalPrices:
    gold_per_gram: float
    silver_per_gram: float
    source: str
    fetched_at: str
    cached: bool = False


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def database_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database_exists() -> None:
    if DATABASE_PATH.exists():
        return
    from scripts.init_db import initialize_database
    from scripts.seed_charities import seed_database

    initialize_database(DATABASE_PATH)
    seed_database(DATABASE_PATH)


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def load_cached_prices() -> dict[str, Any] | None:
    if not PRICES_CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(PRICES_CACHE_PATH.read_text())
        fetched = datetime.fromisoformat(payload["fetched_at"])
        if utc_now() - fetched <= timedelta(hours=PRICE_CACHE_HOURS):
            return payload
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None
    return None


def save_cached_prices(prices: MetalPrices) -> None:
    PRICES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRICES_CACHE_PATH.write_text(
        json.dumps(
            {
                "gold_per_gram": prices.gold_per_gram,
                "silver_per_gram": prices.silver_per_gram,
                "source": prices.source,
                "fetched_at": prices.fetched_at,
            },
            indent=2,
        )
    )


def fetch_prices() -> MetalPrices:
    cached = load_cached_prices()
    if cached:
        return MetalPrices(
            gold_per_gram=float(cached["gold_per_gram"]),
            silver_per_gram=float(cached["silver_per_gram"]),
            source=str(cached.get("source", "cache")),
            fetched_at=str(cached["fetched_at"]),
            cached=True,
        )

    api_url = "https://api.metals.live/v1/spot"
    request_obj = Request(api_url, headers={"User-Agent": "SadaqahLedger/1.0"})
    try:
        with urlopen(request_obj, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        snapshot = {list(entry.keys())[0].lower(): float(list(entry.values())[0]) for entry in data if isinstance(entry, dict) and entry}
        gold_per_gram = snapshot.get("gold", DEFAULT_GOLD_PRICE_PER_GRAM * 31.1035) / 31.1035
        silver_per_gram = snapshot.get("silver", DEFAULT_SILVER_PRICE_PER_GRAM * 31.1035) / 31.1035
        prices = MetalPrices(
            gold_per_gram=round(gold_per_gram, 4),
            silver_per_gram=round(silver_per_gram, 4),
            source="metals.live",
            fetched_at=utc_now().isoformat(),
        )
        save_cached_prices(prices)
        return prices
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        fallback = MetalPrices(
            gold_per_gram=DEFAULT_GOLD_PRICE_PER_GRAM,
            silver_per_gram=DEFAULT_SILVER_PRICE_PER_GRAM,
            source="fallback-static",
            fetched_at=utc_now().isoformat(),
            cached=False,
        )
        save_cached_prices(fallback)
        return fallback


def calculate_zakat(payload: dict[str, Any]) -> dict[str, Any]:
    prices = fetch_prices()
    school = str(payload.get("school", "hanafi")).lower()
    if school not in VALID_SCHOOLS:
        school = "hanafi"

    cash = float(payload.get("cash_savings", 0) or 0)
    gold_grams = float(payload.get("gold_weight_grams", 0) or 0)
    silver_grams = float(payload.get("silver_weight_grams", 0) or 0)
    stocks = float(payload.get("stocks_value", 0) or 0)
    crypto = float(payload.get("crypto_value", 0) or 0)
    inventory = float(payload.get("business_inventory_value", 0) or 0)
    debts = float(payload.get("debts_owed", 0) or 0)

    gold_value = gold_grams * prices.gold_per_gram
    silver_value = silver_grams * prices.silver_per_gram
    total_assets = cash + gold_value + silver_value + stocks + crypto + inventory
    net_assets = max(total_assets - debts, 0)

    nisab_by_gold = GOLD_NISAB_GRAMS * prices.gold_per_gram
    nisab_by_silver = SILVER_NISAB_GRAMS * prices.silver_per_gram
    if school == "hanafi":
        nisab_threshold = min(nisab_by_gold, nisab_by_silver)
        nisab_basis = "silver"
    else:
        nisab_threshold = nisab_by_gold
        nisab_basis = "gold"

    zakat_due = round(net_assets * 0.025, 2) if net_assets >= nisab_threshold else 0.0
    last_payment = payload.get("last_payment_date")
    if last_payment:
        try:
            next_due = date.fromisoformat(last_payment) + timedelta(days=354)
            due_date = next_due.isoformat()
        except ValueError:
            due_date = None
    else:
        due_date = None

    return {
        "prices": prices.__dict__,
        "breakdown": {
            "cash_savings": round(cash, 2),
            "gold_value": round(gold_value, 2),
            "silver_value": round(silver_value, 2),
            "stocks_value": round(stocks, 2),
            "crypto_value": round(crypto, 2),
            "business_inventory_value": round(inventory, 2),
            "debts_owed": round(debts, 2),
        },
        "total_assets": round(total_assets, 2),
        "net_assets": round(net_assets, 2),
        "nisab": {
            "school": school,
            "basis": nisab_basis,
            "threshold": round(nisab_threshold, 2),
            "gold_threshold": round(nisab_by_gold, 2),
            "silver_threshold": round(nisab_by_silver, 2),
            "is_above_nisab": net_assets >= nisab_threshold,
        },
        "zakat_due": zakat_due,
        "due_date": due_date,
    }


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_donation_hash(prev_hash: str, amount: float, charity_hash: str, timestamp: str) -> str:
    raw = f"{prev_hash}|{amount:.2f}|{charity_hash}|{timestamp}"
    return hash_text(raw)


def ledger_integrity_report() -> dict[str, Any]:
    ensure_database_exists()
    conn = database_connection()
    rows = conn.execute(
        "SELECT id, amount, currency, timestamp, charity_hash, prev_hash, donation_hash FROM donations ORDER BY id ASC"
    ).fetchall()
    conn.close()

    expected_prev = "GENESIS"
    issues: list[str] = []
    verified_count = 0
    for row in rows:
        expected_hash = compute_donation_hash(expected_prev, float(row["amount"]), row["charity_hash"], row["timestamp"])
        if row["prev_hash"] != expected_prev:
            issues.append(f"Donation {row['id']} prev_hash mismatch")
        if row["donation_hash"] != expected_hash:
            issues.append(f"Donation {row['id']} donation_hash mismatch")
        expected_prev = row["donation_hash"]
        verified_count += 1

    totals = Counter()
    for row in rows:
        totals[row["charity_hash"]] += float(row["amount"])

    return {
        "valid": not issues,
        "issues": issues,
        "verified_entries": verified_count,
        "latest_hash": expected_prev if rows else "GENESIS",
        "totals_by_charity_hash": {key: round(value, 2) for key, value in totals.items()},
        "entries": [dict(row) for row in rows],
    }


def create_report_pdf(title: str, totals: dict[str, Any], donations: list[dict[str, Any]]) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    pdf.setTitle(title)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(20 * mm, y, APP_TITLE)
    y -= 10 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(20 * mm, y, title)
    y -= 10 * mm
    pdf.setFont("Helvetica", 10)
    for label, value in totals.items():
        pdf.drawString(20 * mm, y, f"{label}: {value}")
        y -= 6 * mm
    y -= 4 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Recent donations")
    y -= 8 * mm
    pdf.setFont("Helvetica", 9)
    for donation in donations[:18]:
        line = f"{donation['timestamp']} | {donation['currency']} {donation['amount']:.2f} | {donation['charity_hash'][:18]}..."
        pdf.drawString(20 * mm, y, line)
        y -= 5 * mm
        if y < 20 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica", 9)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


@app.route("/")
def index() -> Any:
    ensure_database_exists()
    return app.send_static_file("index.html")


@app.route("/api/health")
def health() -> Any:
    ensure_database_exists()
    return jsonify({"status": "ok", "database": str(DATABASE_PATH)})


@app.route("/api/prices")
def prices() -> Any:
    return jsonify(fetch_prices().__dict__)


@app.post("/api/zakat/calculate")
def zakat_calculation() -> Any:
    payload = request.get_json(silent=True) or {}
    return jsonify(calculate_zakat(payload))


@app.get("/api/charities")
def charities() -> Any:
    ensure_database_exists()
    query = request.args.get("q", "").strip().lower()
    country = request.args.get("country", "").strip().upper()
    cause = request.args.get("cause", "").strip().lower()
    verified_only = request.args.get("verified_only", "false").lower() == "true"

    sql = "SELECT * FROM charities WHERE 1=1"
    params: list[Any] = []
    if query:
        sql += " AND (LOWER(name) LIKE ? OR LOWER(website) LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like])
    if country:
        sql += " AND country = ?"
        params.append(country)
    if cause:
        sql += " AND cause = ?"
        params.append(cause)
    if verified_only:
        sql += " AND verified_at IS NOT NULL"
    sql += " ORDER BY fraud_count ASC, name ASC LIMIT 200"

    conn = database_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return jsonify([row_to_dict(row) for row in rows])


@app.post("/api/donations")
def record_donation() -> Any:
    ensure_database_exists()
    payload = request.get_json(silent=True) or {}
    charity_name = str(payload.get("charity_name", "")).strip()
    amount = float(payload.get("amount", 0) or 0)
    currency = str(payload.get("currency", "USD")).upper()
    if not charity_name or amount <= 0:
        return jsonify({"error": "charity_name and positive amount are required"}), 400

    charity_hash = hash_text(charity_name.lower())
    timestamp = payload.get("timestamp") or utc_now().replace(microsecond=0).isoformat()
    conn = database_connection()
    previous_row = conn.execute("SELECT donation_hash FROM donations ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = previous_row["donation_hash"] if previous_row else "GENESIS"
    donation_hash = compute_donation_hash(prev_hash, amount, charity_hash, timestamp)
    conn.execute(
        "INSERT INTO donations (charity_hash, amount, currency, timestamp, prev_hash, donation_hash) VALUES (?, ?, ?, ?, ?, ?)",
        (charity_hash, amount, currency, timestamp, prev_hash, donation_hash),
    )
    conn.commit()
    donation_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return jsonify(
        {
            "id": donation_id,
            "charity_hash": charity_hash,
            "amount": round(amount, 2),
            "currency": currency,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
            "donation_hash": donation_hash,
        }
    ), 201


@app.get("/api/ledger")
def donation_ledger() -> Any:
    return jsonify(ledger_integrity_report())


@app.post("/api/reminders")
def create_reminder() -> Any:
    ensure_database_exists()
    payload = request.get_json(silent=True) or {}
    zakat_due_date = payload.get("zakat_due_date")
    telegram_id = str(payload.get("telegram_id", "")).strip()
    email = str(payload.get("email", "")).strip()
    reminder_enabled = bool(payload.get("reminder_enabled", True))
    if not zakat_due_date:
        return jsonify({"error": "zakat_due_date is required"}), 400
    try:
        date.fromisoformat(zakat_due_date)
    except ValueError:
        return jsonify({"error": "zakat_due_date must be ISO format YYYY-MM-DD"}), 400
    conn = database_connection()
    conn.execute(
        "INSERT INTO users (telegram_id, email, zakat_due_date, reminder_enabled, created_at) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, email, zakat_due_date, 1 if reminder_enabled else 0, utc_now().isoformat()),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    schedule = []
    due = date.fromisoformat(zakat_due_date)
    for offset in REMINDER_OFFSETS:
        schedule.append({"offset_days": offset, "scheduled_for": (due - timedelta(days=offset)).isoformat()})
    return jsonify({"id": user_id, "schedule": schedule}), 201


@app.get("/api/reminders/due")
def due_reminders() -> Any:
    ensure_database_exists()
    target_date = request.args.get("on") or date.today().isoformat()
    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        return jsonify({"error": "Invalid date"}), 400
    conn = database_connection()
    users = conn.execute("SELECT * FROM users WHERE reminder_enabled = 1").fetchall()
    conn.close()
    due_items: list[dict[str, Any]] = []
    for user in users:
        due_date = date.fromisoformat(user["zakat_due_date"])
        delta = (due_date - target).days
        if delta in REMINDER_OFFSETS:
            due_items.append(
                {
                    "user_id": user["id"],
                    "telegram_id": user["telegram_id"],
                    "email": user["email"],
                    "zakat_due_date": user["zakat_due_date"],
                    "days_until_due": delta,
                    "message": f"Your Zakat due date is {user['zakat_due_date']}. Please review your annual obligation.",
                }
            )
    return jsonify(due_items)


@app.get("/api/reports/charity/<charity_hash>")
def charity_report(charity_hash: str) -> Any:
    ensure_database_exists()
    conn = database_connection()
    donations = conn.execute(
        "SELECT * FROM donations WHERE charity_hash = ? ORDER BY timestamp DESC", (charity_hash,)
    ).fetchall()
    conn.close()
    donation_dicts = [row_to_dict(row) for row in donations]
    total_amount = round(sum(float(item["amount"]) for item in donation_dicts), 2)
    total_donors = len(donation_dicts)
    avg_donation = round(total_amount / total_donors, 2) if total_donors else 0.0
    context = {
        "charity_hash": charity_hash,
        "generated_at": utc_now().isoformat(),
        "total_amount": total_amount,
        "total_donors": total_donors,
        "average_donation": avg_donation,
        "donations": donation_dicts,
    }
    as_pdf = request.args.get("format", "html").lower() == "pdf"
    if as_pdf:
        pdf = create_report_pdf(
            title=f"Impact report for {charity_hash[:12]}",
            totals={
                "Charity hash": charity_hash,
                "Generated": context["generated_at"],
                "Total donations": total_amount,
                "Total donors": total_donors,
                "Average donation": avg_donation,
            },
            donations=donation_dicts,
        )
        return send_file(pdf, mimetype="application/pdf", download_name=f"impact-report-{charity_hash[:12]}.pdf")
    return render_template("report.html", **context)


if __name__ == "__main__":
    ensure_database_exists()
    app.run(host="0.0.0.0", port=5000, debug=False)
