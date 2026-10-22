"""Validate the checked-in data files and print a concise report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.trend_data import validate_datasets  # noqa: E402


if __name__ == "__main__":
    result = validate_datasets()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)
