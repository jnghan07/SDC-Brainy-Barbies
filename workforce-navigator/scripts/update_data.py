"""Dry-run-first importer for manually reviewed CSV records.

This tool never contacts external services. It can merge a reviewed CSV into
one of the four datasets, validates proposed rows against all datasets, and
keeps verified rows protected from unverified replacements.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.trend_data import DATA_DIR, REQUIRED_COLUMNS, load_datasets, validate_datasets  # noqa: E402

KEY_COLUMNS = {
    "roles": ("role_id",),
    "trends": ("trend_id",),
    "courses": ("course_id",),
    "sdg_mappings": ("role_id", "sdg_id"),
}


def _row_key(row: dict[str, str], dataset: str) -> tuple[str, ...]:
    return tuple(row[column].strip() for column in KEY_COLUMNS[dataset])


def _validate_frames(frames: dict[str, pd.DataFrame]) -> list[str]:
    """Validate a proposed in-memory snapshot through the public validator."""
    with tempfile.TemporaryDirectory(prefix="workforce-data-check-") as temp_dir:
        for name, frame in frames.items():
            frame.to_csv(Path(temp_dir) / f"{name}.csv", index=False)
        return validate_datasets(temp_dir)["errors"]


def plan_csv_update(
    dataset: str,
    input_csv: str | Path,
    *,
    data_dir: str | Path | None = None,
    apply: bool = False,
    confirm_verified_updates: bool = False,
) -> dict[str, Any]:
    """Validate and optionally merge an import file into one dataset.

    A dry run is the default. ``added`` and ``changed`` describe valid planned
    rows even in dry-run mode; ``applied`` says whether the CSV was written.
    Candidate/unverified additions and changes also increment ``needs_review``.
    Verified rows are never replaced by an unverified row. Changing an existing
    verified row requires a verified incoming row and
    ``confirm_verified_updates=True``.
    """
    if dataset not in REQUIRED_COLUMNS:
        raise ValueError(f"Unknown dataset {dataset!r}; choose one of {sorted(REQUIRED_COLUMNS)}.")
    directory = Path(data_dir).expanduser().resolve() if data_dir is not None else DATA_DIR
    target_path = directory / f"{dataset}.csv"
    input_path = Path(input_csv).expanduser().resolve()
    if input_path == target_path.resolve():
        raise ValueError("The input CSV must be separate from the destination dataset.")
    if not input_path.is_file():
        raise FileNotFoundError(f"Import CSV not found: {input_path}")

    frames = load_datasets(directory)
    try:
        incoming = pd.read_csv(input_path, dtype=str, keep_default_na=False, encoding="utf-8")
    except (pd.errors.ParserError, UnicodeDecodeError, OSError, ValueError) as exc:
        raise ValueError(f"Cannot read import CSV at {input_path}: {exc}") from exc

    expected = list(REQUIRED_COLUMNS[dataset])
    missing = sorted(set(expected) - set(incoming.columns))
    extra = sorted(set(incoming.columns) - set(expected))
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected columns: {', '.join(extra)}")
        raise ValueError(f"Import CSV must match the {dataset}.csv schema exactly ({'; '.join(details)}).")
    incoming = incoming.loc[:, expected]

    report: dict[str, Any] = {
        "dataset": dataset,
        "dry_run": not apply,
        "applied": False,
        "added": 0,
        "changed": 0,
        "unchanged": 0,
        "rejected": 0,
        "needs_review": 0,
        "rejections": [],
        "review_items": [],
    }
    working = {name: frame.copy() for name, frame in frames.items()}
    seen_input_keys: set[tuple[str, ...]] = set()
    key_columns = KEY_COLUMNS[dataset]
    current = working[dataset]

    for csv_row_number, (_, series) in enumerate(incoming.iterrows(), start=2):
        record = {column: str(series[column]) for column in expected}
        key = _row_key(record, dataset)
        key_label = "/".join(key) if all(key) else "(blank key)"
        if not all(key):
            report["rejected"] += 1
            report["rejections"].append(
                {"row": csv_row_number, "key": key_label, "reason": f"{', '.join(key_columns)} must not be blank."}
            )
            continue
        if key in seen_input_keys:
            report["rejected"] += 1
            report["rejections"].append(
                {"row": csv_row_number, "key": key_label, "reason": "Duplicate key in the import CSV."}
            )
            continue
        seen_input_keys.add(key)

        key_mask = pd.Series(True, index=current.index)
        for column, value in zip(key_columns, key):
            key_mask &= current[column].eq(value)
        matching_indices = current.index[key_mask].tolist()
        is_existing = bool(matching_indices)
        if is_existing:
            row_index = matching_indices[0]
            existing = {column: str(current.loc[row_index, column]) for column in expected}
            if existing == record:
                report["unchanged"] += 1
                continue
            if existing["verification_status"] == "verified":
                if record["verification_status"] != "verified":
                    report["needs_review"] += 1
                    report["review_items"].append(
                        {
                            "row": csv_row_number,
                            "key": key_label,
                            "reason": "An unverified import cannot replace a verified record.",
                        }
                    )
                    continue
                if not confirm_verified_updates:
                    report["needs_review"] += 1
                    report["review_items"].append(
                        {
                            "row": csv_row_number,
                            "key": key_label,
                            "reason": "Changing a verified record requires --confirm-verified-updates.",
                        }
                    )
                    continue

        proposed = {name: frame.copy() for name, frame in working.items()}
        if is_existing:
            proposed[dataset].loc[matching_indices[0], expected] = [record[column] for column in expected]
        else:
            proposed[dataset] = pd.concat(
                [proposed[dataset], pd.DataFrame([record], columns=expected)],
                ignore_index=True,
            )

        errors = _validate_frames(proposed)
        if errors:
            report["rejected"] += 1
            report["rejections"].append(
                {"row": csv_row_number, "key": key_label, "reason": " | ".join(errors)}
            )
            continue

        working = proposed
        current = working[dataset]
        report["changed" if is_existing else "added"] += 1
        if record["verification_status"] != "verified":
            report["needs_review"] += 1
            report["review_items"].append(
                {
                    "row": csv_row_number,
                    "key": key_label,
                    "reason": "Record is not verified and must be reviewed before use as evidence.",
                }
            )

    if apply and (report["added"] or report["changed"]):
        errors = _validate_frames(working)
        if errors:
            raise ValueError("Merged dataset failed final validation: " + " | ".join(errors))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=target_path.parent,
                prefix=f".{target_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                working[dataset].to_csv(temp_file, index=False)
            os.replace(temp_path, target_path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        report["applied"] = True
    return report


def _print_validation_summary(data_dir: str | None = None) -> int:
    result = validate_datasets(data_dir)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(REQUIRED_COLUMNS), help="Dataset to import into.")
    parser.add_argument("--input", help="Reviewed CSV file with the exact destination schema.")
    parser.add_argument("--data-dir", help="Dataset directory; defaults to this project's data/ folder.")
    parser.add_argument("--apply", action="store_true", help="Write valid planned changes. Omit for dry run.")
    parser.add_argument(
        "--confirm-verified-updates",
        action="store_true",
        help="Allow verified input rows to replace existing verified rows.",
    )
    args = parser.parse_args()

    if not args.dataset and not args.input:
        return _print_validation_summary(args.data_dir)
    if not args.dataset or not args.input:
        parser.error("--dataset and --input must be supplied together.")
    if args.confirm_verified_updates and not args.apply:
        parser.error("--confirm-verified-updates requires --apply.")
    try:
        report = plan_csv_update(
            args.dataset,
            args.input,
            data_dir=args.data_dir,
            apply=args.apply,
            confirm_verified_updates=args.confirm_verified_updates,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 1 if report["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
