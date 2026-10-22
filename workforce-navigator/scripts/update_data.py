"""Manual-edit preflight for dataset maintainers.

Edit reviewed CSV rows by hand, then run this script before committing. It
validates the files and deliberately does not fetch or scrape external sources.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.trend_data import validate_datasets  # noqa: E402


if __name__ == "__main__":
    result = validate_datasets()
    for name, count in result["record_counts"].items():
        print(f"{name}: {count} record(s)")
    for warning in result["warnings"]:
        print(f"NOTE: {warning}")
    for error in result["errors"]:
        print(f"ERROR: {error}")
    print("Data preflight passed." if result["valid"] else "Data preflight failed.")
    raise SystemExit(0 if result["valid"] else 1)
