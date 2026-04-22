#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import ledger_integrity_report


if __name__ == "__main__":
    print(json.dumps(ledger_integrity_report(), indent=2))
