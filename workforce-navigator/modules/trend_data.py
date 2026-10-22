"""Validated pandas accessors for the Workforce Navigator CSV datasets.

All table accessors return pandas DataFrames except ``get_role`` (a Series)
and ``get_role_skills`` (a list of canonical skill names). Dataset failures are
reported as :class:`DatasetValidationError`; unknown role IDs raise KeyError.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "roles": (
        "role_id",
        "role_name",
        "role_description",
        "required_skills",
        "skill_weights",
        "occupation_source",
        "source_url",
        "verification_status",
        "record_notes",
    ),
    "trends": (
        "trend_id",
        "role_id",
        "skill_name",
        "trend_direction",
        "evidence_summary",
        "source_name",
        "source_url",
        "publication_date",
        "retrieved_date",
        "evidence_type",
        "confidence_level",
        "verification_status",
        "is_scenario_input",
        "scenario_relevance",
        "proposed_scenario_adjustment",
        "adjustment_basis",
        "interpretation_limitations",
    ),
    "courses": (
        "course_id",
        "course_name",
        "provider",
        "target_skills",
        "course_url",
        "cost_status",
        "availability_status",
        "last_verified_date",
        "source_url",
        "verification_status",
        "record_notes",
    ),
    "sdg_mappings": (
        "role_id",
        "sdg_id",
        "sdg_name",
        "mapping_rationale",
        "supporting_evidence",
        "source_url",
        "verification_status",
        "record_notes",
    ),
}

VERIFICATION_STATUSES = {"verified", "candidate_unverified", "requires_verification"}
TREND_DIRECTIONS = {"increasing", "stable", "decreasing", "uncertain"}
EVIDENCE_TYPES = {"direct", "interpretation", "report", "dataset", "forecast", "other", "unknown"}
CONFIDENCE_LEVELS = {"low", "medium", "high", "not_assessed"}
COST_STATUSES = {"free", "paid", "mixed", "unknown", "requires_verification"}
AVAILABILITY_STATUSES = {
    "available",
    "unavailable",
    "unknown",
    "requires_verification",
}
SCENARIO_INPUT_FLAGS = {"true", "false"}

# Canonical skill names are the exact labels used in CSV values. Aliases are
# normalized by case and whitespace and never stored back into source files.
CANONICAL_SKILLS = {
    "Analytical Thinking",
    "Cloud Computing",
    "Communication",
    "Content Strategy",
    "Cybersecurity",
    "Data Analysis",
    "Data Visualization",
    "Digital Marketing",
    "Environmental Analysis",
    "Excel",
    "Figma",
    "Financial Analysis",
    "Git",
    "Human Resources",
    "JavaScript",
    "Logistics",
    "Machine Learning",
    "Network Security",
    "People Analytics",
    "Project Management",
    "Python",
    "Risk Assessment",
    "SEO",
    "SQL",
    "Software Development",
    "Statistics",
    "Supply Chain Management",
    "Sustainability Reporting",
    "UI/UX Design",
    "User Research",
}
_SKILL_LOOKUP = {skill.casefold(): skill for skill in CANONICAL_SKILLS}
_SKILL_ALIASES = {
    "ml": "Machine Learning",
    "ai/ml": "Machine Learning",
    "machine learning (ml)": "Machine Learning",
    "ux": "UI/UX Design",
    "ui": "UI/UX Design",
    "ux/ui": "UI/UX Design",
    "data visualisation": "Data Visualization",
    "human resource management": "Human Resources",
    "search engine optimisation": "SEO",
    "search engine optimization": "SEO",
}
_SCENARIO_COLUMNS = (
    "trend_id",
    "role_id",
    "skill_name",
    "trend_direction",
    "evidence_summary",
    "source_name",
    "source_url",
    "publication_date",
    "retrieved_date",
    "confidence_level",
    "scenario_relevance",
    "proposed_scenario_adjustment",
    "adjustment_basis",
    "interpretation_limitations",
)


class DatasetValidationError(ValueError):
    """Raised when one or more CSV datasets are missing or invalid."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Dataset validation failed:\n- " + "\n- ".join(errors))


def canonicalize_skill(skill: str) -> str:
    """Return a canonical skill label, accepting documented aliases.

    Raises ValueError when ``skill`` is not in the documented vocabulary.
    """
    normalized = " ".join(str(skill).strip().split()).casefold()
    canonical = _SKILL_LOOKUP.get(normalized) or _SKILL_LOOKUP.get(
        _SKILL_ALIASES.get(normalized, "").casefold()
    )
    if canonical is None:
        raise ValueError(f"Unknown skill {skill!r}; add it to the documented canonical vocabulary first.")
    return canonical


def _resolve_data_dir(data_dir: str | Path | None) -> Path:
    return Path(data_dir).expanduser().resolve() if data_dir is not None else DATA_DIR


def _read_csv(path: Path, dataset_name: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"Missing required dataset file: {path}") from exc
    except (pd.errors.ParserError, UnicodeDecodeError, OSError, ValueError) as exc:
        raise ValueError(f"Cannot read {dataset_name} dataset at {path}: {exc}") from exc


def _load_raw(data_dir: str | Path | None = None) -> tuple[dict[str, pd.DataFrame], list[str]]:
    directory = _resolve_data_dir(data_dir)
    datasets: dict[str, pd.DataFrame] = {}
    errors: list[str] = []
    for name in REQUIRED_COLUMNS:
        try:
            datasets[name] = _read_csv(directory / f"{name}.csv", name)
        except ValueError as exc:
            errors.append(str(exc))
    return datasets, errors


def _json_cell(value: str, context: str) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"{context} must contain valid JSON: {exc}") from exc


def _validate_iso_date(value: str, context: str, errors: list[str]) -> None:
    if not value:
        return
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        errors.append(f"{context} must be a real ISO date in YYYY-MM-DD format; got {value!r}.")
        return
    if parsed.isoformat() != value:
        errors.append(f"{context} must use YYYY-MM-DD format; got {value!r}.")


def _validate_url(value: str, context: str, errors: list[str]) -> None:
    if not value:
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{context} must be an absolute http(s) URL or blank; got {value!r}.")


def _validate_status(frame: pd.DataFrame, dataset: str, errors: list[str]) -> None:
    for row_num, value in enumerate(frame.get("verification_status", []), start=2):
        if value not in VERIFICATION_STATUSES:
            errors.append(
                f"{dataset}.csv row {row_num}: verification_status must be one of "
                f"{sorted(VERIFICATION_STATUSES)}; got {value!r}."
            )


def _validate_skills_json(value: str, context: str, errors: list[str], *, allow_weights: bool = False) -> None:
    parsed = _json_cell(value, context)
    if allow_weights:
        if not isinstance(parsed, dict):
            errors.append(f"{context} must be a JSON object mapping canonical skills to optional weights.")
            return
        for raw_skill, weight in parsed.items():
            try:
                canonicalize_skill(raw_skill)
            except ValueError as exc:
                errors.append(f"{context}: {exc}")
            if weight is not None and (
                not isinstance(weight, (int, float)) or isinstance(weight, bool) or not 0 <= weight <= 1
            ):
                errors.append(f"{context}: weights must be numbers from 0 to 1 or null; got {weight!r}.")
        return

    if not isinstance(parsed, list):
        errors.append(f"{context} must be a JSON array of canonical skill names.")
        return
    if any(not isinstance(item, str) for item in parsed):
        errors.append(f"{context} must contain only string skill names.")
        return
    if len(parsed) != len(set(parsed)):
        errors.append(f"{context} contains duplicate skills.")
    for raw_skill in parsed:
        try:
            canonicalize_skill(raw_skill)
        except ValueError as exc:
            errors.append(f"{context}: {exc}")


def _validate_dataset_values(datasets: dict[str, pd.DataFrame], errors: list[str]) -> None:
    roles = datasets.get("roles")
    trends = datasets.get("trends")
    courses = datasets.get("courses")
    mappings = datasets.get("sdg_mappings")
    if roles is None or trends is None or courses is None or mappings is None:
        return

    for dataset, frame in datasets.items():
        missing_columns = sorted(set(REQUIRED_COLUMNS[dataset]) - set(frame.columns))
        if missing_columns:
            errors.append(f"{dataset}.csv is missing required columns: {', '.join(missing_columns)}.")
    if any(set(REQUIRED_COLUMNS[name]) - set(frame.columns) for name, frame in datasets.items()):
        return

    key_columns = {"roles": ["role_id"], "trends": ["trend_id"], "courses": ["course_id"]}
    for dataset, columns in key_columns.items():
        frame = datasets[dataset]
        for key in columns:
            blank_rows = frame.index[frame[key].str.strip().eq("")].tolist()
            if blank_rows:
                row_labels = ", ".join(str(i + 2) for i in blank_rows)
                errors.append(f"{dataset}.csv has blank {key} value(s) on row(s): {row_labels}.")
            duplicates = frame.loc[frame[key].ne(""), key]
            duplicate_values = sorted(duplicates[duplicates.duplicated(keep=False)].unique().tolist())
            if duplicate_values:
                errors.append(f"{dataset}.csv has duplicate {key} value(s): {', '.join(duplicate_values)}.")

    mapping_keys = mappings[["role_id", "sdg_id"]].astype(str).agg("|".join, axis=1)
    duplicate_mapping_keys = sorted(mapping_keys[mapping_keys.duplicated(keep=False)].unique().tolist())
    if duplicate_mapping_keys:
        errors.append("sdg_mappings.csv has duplicate role_id/sdg_id pair(s): " + ", ".join(duplicate_mapping_keys) + ".")

    _validate_status(roles, "roles", errors)
    _validate_status(trends, "trends", errors)
    _validate_status(courses, "courses", errors)
    _validate_status(mappings, "sdg_mappings", errors)

    for idx, row in roles.iterrows():
        line = idx + 2
        for column in ("role_name", "role_description", "required_skills", "skill_weights"):
            if not row[column].strip():
                errors.append(f"roles.csv row {line}: {column} must not be blank.")
        if row["required_skills"].strip():
            _validate_skills_json(row["required_skills"], f"roles.csv row {line} required_skills", errors)
        if row["skill_weights"].strip():
            _validate_skills_json(
                row["skill_weights"], f"roles.csv row {line} skill_weights", errors, allow_weights=True
            )
        _validate_url(row["source_url"], f"roles.csv row {line} source_url", errors)
        if row["verification_status"] == "verified":
            if not row["occupation_source"].strip() or not row["source_url"].strip():
                errors.append(f"roles.csv row {line}: verified roles require occupation_source and source_url.")

    role_ids = set(roles["role_id"])
    for idx, row in trends.iterrows():
        line = idx + 2
        if row["role_id"] not in role_ids:
            errors.append(f"trends.csv row {line}: role_id {row['role_id']!r} does not exist in roles.csv.")
        if row["trend_direction"] not in TREND_DIRECTIONS:
            errors.append(f"trends.csv row {line}: invalid trend_direction {row['trend_direction']!r}.")
        if row["evidence_type"] and row["evidence_type"] not in EVIDENCE_TYPES:
            errors.append(f"trends.csv row {line}: invalid evidence_type {row['evidence_type']!r}.")
        if row["confidence_level"] and row["confidence_level"] not in CONFIDENCE_LEVELS:
            errors.append(f"trends.csv row {line}: invalid confidence_level {row['confidence_level']!r}.")
        if row["skill_name"]:
            try:
                canonicalize_skill(row["skill_name"])
            except ValueError as exc:
                errors.append(f"trends.csv row {line}: {exc}")
        for column in ("publication_date", "retrieved_date"):
            _validate_iso_date(row[column], f"trends.csv row {line} {column}", errors)
        _validate_url(row["source_url"], f"trends.csv row {line} source_url", errors)
        if row["verification_status"] == "verified":
            required = (
                "skill_name",
                "evidence_summary",
                "source_name",
                "source_url",
                "publication_date",
                "retrieved_date",
                "evidence_type",
                "confidence_level",
            )
            missing = [column for column in required if not row[column].strip()]
            if missing:
                errors.append(f"trends.csv row {line}: verified trend requires {', '.join(missing)}.")
        if row["is_scenario_input"].casefold() not in SCENARIO_INPUT_FLAGS:
            errors.append(f"trends.csv row {line}: is_scenario_input must be true or false.")
        if row["is_scenario_input"].casefold() == "true" and row["verification_status"] != "verified":
            errors.append(f"trends.csv row {line}: scenario inputs must be verified evidence.")
        if row["is_scenario_input"].casefold() == "true":
            scenario_fields = (
                "scenario_relevance",
                "proposed_scenario_adjustment",
                "adjustment_basis",
                "interpretation_limitations",
            )
            missing = [column for column in scenario_fields if not row[column].strip()]
            if missing:
                errors.append(f"trends.csv row {line}: scenario inputs require {', '.join(missing)}.")

    for idx, row in courses.iterrows():
        line = idx + 2
        if row["target_skills"].strip():
            _validate_skills_json(row["target_skills"], f"courses.csv row {line} target_skills", errors)
        elif row["verification_status"] == "verified":
            errors.append(f"courses.csv row {line}: verified courses require target_skills.")
        if row["cost_status"] and row["cost_status"] not in COST_STATUSES:
            errors.append(f"courses.csv row {line}: invalid cost_status {row['cost_status']!r}.")
        if row["availability_status"] and row["availability_status"] not in AVAILABILITY_STATUSES:
            errors.append(f"courses.csv row {line}: invalid availability_status {row['availability_status']!r}.")
        _validate_iso_date(row["last_verified_date"], f"courses.csv row {line} last_verified_date", errors)
        _validate_url(row["course_url"], f"courses.csv row {line} course_url", errors)
        _validate_url(row["source_url"], f"courses.csv row {line} source_url", errors)
        if row["verification_status"] == "verified":
            required = ("course_name", "provider", "course_url", "last_verified_date", "source_url")
            missing = [column for column in required if not row[column].strip()]
            if missing:
                errors.append(f"courses.csv row {line}: verified course requires {', '.join(missing)}.")

    for idx, row in mappings.iterrows():
        line = idx + 2
        if row["role_id"] not in role_ids:
            errors.append(f"sdg_mappings.csv row {line}: role_id {row['role_id']!r} does not exist in roles.csv.")
        try:
            sdg_id = int(row["sdg_id"])
            if not 1 <= sdg_id <= 17:
                raise ValueError
        except ValueError:
            errors.append(f"sdg_mappings.csv row {line}: sdg_id must be an integer from 1 to 17.")
        if not row["mapping_rationale"].strip():
            errors.append(f"sdg_mappings.csv row {line}: mapping_rationale must not be blank.")
        _validate_url(row["source_url"], f"sdg_mappings.csv row {line} source_url", errors)
        if row["verification_status"] == "verified":
            required = ("sdg_name", "supporting_evidence", "source_url")
            missing = [column for column in required if not row[column].strip()]
            if missing:
                errors.append(f"sdg_mappings.csv row {line}: verified mapping requires {', '.join(missing)}.")


def validate_datasets(data_dir: str | Path | None = None) -> dict[str, Any]:
    """Return validation summary: ``valid``, ``errors``, ``warnings``, and counts.

    ``data_dir`` is an optional directory override intended for fixtures and
    alternate deployments. Empty trend/course datasets are valid and reported
    as warnings rather than errors.
    """
    datasets, errors = _load_raw(data_dir)
    _validate_dataset_values(datasets, errors)
    counts = {name: len(frame) for name, frame in datasets.items()}
    warnings = [
        f"{name}.csv has no records yet; the schema is ready for verified data."
        for name in ("trends", "courses")
        if counts.get(name) == 0 and name in datasets
    ]
    return {"valid": not errors, "errors": errors, "warnings": warnings, "record_counts": counts}


def load_datasets(data_dir: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Load and validate all four CSV files, returning a name-to-DataFrame map.

    Raises DatasetValidationError rather than dropping invalid rows or files.
    """
    result = validate_datasets(data_dir)
    if not result["valid"]:
        raise DatasetValidationError(result["errors"])
    datasets, errors = _load_raw(data_dir)
    if errors:
        raise DatasetValidationError(errors)
    return datasets


def _ensure_role_exists(role_id: str, roles: pd.DataFrame) -> None:
    if role_id not in set(roles["role_id"]):
        raise KeyError(f"Unknown role_id {role_id!r}. Use get_roles() to list available role IDs.")


def get_roles(*, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Return all role records as a validated pandas DataFrame."""
    return load_datasets(data_dir)["roles"].copy()


def get_role(role_id: str, *, data_dir: str | Path | None = None) -> pd.Series:
    """Return one role as a pandas Series; raise KeyError when not found."""
    roles = get_roles(data_dir=data_dir)
    _ensure_role_exists(role_id, roles)
    return roles.loc[roles["role_id"].eq(role_id)].iloc[0].copy()


def get_trends(role_id: str | None = None, *, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Return trend records, optionally filtered by known role ID."""
    datasets = load_datasets(data_dir)
    trends = datasets["trends"].copy()
    if role_id is not None:
        _ensure_role_exists(role_id, datasets["roles"])
        trends = trends.loc[trends["role_id"].eq(role_id)]
    return trends.copy()


def get_courses(skill: str | None = None, *, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Return verified course records, optionally matched by canonical skill or alias."""
    courses = load_datasets(data_dir)["courses"]
    verified = courses.loc[courses["verification_status"].eq("verified")].copy()
    if skill is None:
        return verified
    canonical = canonicalize_skill(skill)
    matching = verified["target_skills"].map(
        lambda cell: canonical in [canonicalize_skill(item) for item in _json_cell(cell, "target_skills")]
    )
    return verified.loc[matching].copy()


def get_sdg_mappings(
    role_id: str | None = None, *, data_dir: str | Path | None = None
) -> pd.DataFrame:
    """Return candidate and verified SDG mappings, optionally filtered by role ID."""
    datasets = load_datasets(data_dir)
    mappings = datasets["sdg_mappings"].copy()
    if role_id is not None:
        _ensure_role_exists(role_id, datasets["roles"])
        mappings = mappings.loc[mappings["role_id"].eq(role_id)]
    return mappings.copy()


def get_role_skills(role_id: str, *, data_dir: str | Path | None = None) -> list[str]:
    """Return a role's canonical skill labels as a list; raise KeyError if absent."""
    role = get_role(role_id, data_dir=data_dir)
    return [canonicalize_skill(item) for item in _json_cell(role["required_skills"], "required_skills")]


def get_scenario_inputs(*, data_dir: str | Path | None = None) -> pd.DataFrame:
    """Return verified trend evidence explicitly marked for scenario consideration.

    This provides data only and does not calculate scenarios. The starter
    dataset returns an empty DataFrame with these columns until reviewed evidence
    and a documented adjustment basis are added.
    """
    trends = load_datasets(data_dir)["trends"]
    selected = trends.loc[trends["is_scenario_input"].str.casefold().eq("true"), list(_SCENARIO_COLUMNS)]
    return selected.copy()
