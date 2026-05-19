from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATABASE_PATH = DATA_DIR / "sadaqahledger.db"
PRICES_CACHE_PATH = DATA_DIR / "prices_cache.json"
DEFAULT_GOLD_PRICE_PER_GRAM = float(os.getenv("SADAQAH_GOLD_PRICE_PER_GRAM", "74.50"))
DEFAULT_SILVER_PRICE_PER_GRAM = float(os.getenv("SADAQAH_SILVER_PRICE_PER_GRAM", "0.87"))
PRICE_CACHE_HOURS = int(os.getenv("SADAQAH_PRICE_CACHE_HOURS", "12"))
SECRET_KEY = os.getenv("SECRET_KEY", "sadaqahledger-dev-key")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
REPORT_CURRENCY = os.getenv("REPORT_CURRENCY", "USD")
APP_TITLE = "SadaqahLedger"
