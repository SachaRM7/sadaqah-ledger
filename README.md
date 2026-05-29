# SadaqahLedger

SadaqahLedger is a lightweight Flask + vanilla JavaScript web application for:
- accurate Zakat estimation with live/cached gold and silver prices,
- browsing a pre-seeded registry of Islamic charities,
- recording anonymous donations into a tamper-evident SHA-256 ledger,
- generating impact reports in HTML or PDF,
- registering Zakat reminders for Telegram/email workflows.

## Features

### Zakat calculator
- Supports cash, gold, silver, stocks, crypto, business inventory, and debts.
- Uses Hanafi nisab by default, with a toggle for other schools.
- Pulls metal prices from metals.live when available and falls back to static cached values.

### Charity verification registry
- Ships with a CSV seed dataset containing 200 charity records across multiple countries.
- Search by country, cause, or free-text name.
- Tracks verification source, verification date, and fraud-report count.

### Public donation ledger
- Donation entries store only amount, currency, timestamp, charity hash, previous hash, and current hash.
- Chain integrity can be verified from the UI or with scripts/verify_ledger.py.

### Impact reports
- HTML report page for any charity hash.
- PDF export via ReportLab at /api/reports/charity/<charity_hash>?format=pdf.

### Reminder system
- Stores reminder preferences in SQLite.
- Exposes /api/reminders/due?on=YYYY-MM-DD so an external cron or bot can deliver reminders.

## Project layout

/root/.hermes/agents/coder/code/20260419/
├── app.py
├── config.py
├── requirements.txt
├── Dockerfile
├── README.md
├── data/
│   ├── charities_seed.csv
│   └── sadaqahledger.db
├── scripts/
│   ├── init_db.py
│   ├── seed_charities.py
│   └── verify_ledger.py
├── static/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── calculator.js
│       ├── ledger.js
│       └── reminders.js
└── templates/report.html

## Setup

### Local Python setup

```bash
cd /root/.hermes/agents/coder/code/20260419
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_charities.py
python app.py
```

Open http://127.0.0.1:5000

### Docker setup

```bash
cd /root/.hermes/agents/coder/code/20260419
docker build -t sadaqahledger .
docker run --rm -p 5000:5000 sadaqahledger
```

## Example API usage

### Calculate Zakat

```bash
curl -s http://127.0.0.1:5000/api/zakat/calculate   -H 'Content-Type: application/json'   -d '{
    "cash_savings": 10000,
    "gold_weight_grams": 50,
    "silver_weight_grams": 0,
    "stocks_value": 2000,
    "crypto_value": 500,
    "business_inventory_value": 0,
    "debts_owed": 1000,
    "school": "hanafi"
  }' | python -m json.tool
```

### Record a donation

```bash
curl -s http://127.0.0.1:5000/api/donations   -H 'Content-Type: application/json'   -d '{"charity_name":"Islamic Relief","amount":50,"currency":"USD"}' | python -m json.tool
```

### Verify ledger integrity

```bash
python scripts/verify_ledger.py
```

## Islamic jurisprudence notes

- This implementation uses the common baseline formula: max(total_assets - debts, 0) * 2.5% when the user is above nisab.
- Hanafi mode uses the lower of gold and silver nisab values, which typically means silver-based eligibility in practice.
- Other schools in this v1 use the gold threshold as a simpler conservative default.
- Lunar due-date estimation is approximate: the app adds 354 days to the previous payment date.
- This project is educational open-source software, not a fatwa. Users should consult a qualified scholar for edge cases involving business assets, mixed debt treatment, retirement accounts, or complex crypto holdings.

## License

MIT
