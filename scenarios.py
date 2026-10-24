"""Scenario weights for match.score_roles, using only the Python standard library.

Usage: score_roles(skills, roles, weights=get_weights("moderate"))

Reads data/trends.csv if present; missing trends mean neutral weights. Synthetic
examples live only in tests, not here. Optional growth_rate values are signed
percentage points (10 or 10% means ten percent), NOT decimal fractions.
Role IDs are provenance only: this API returns global skill weights. Conflicting
rows for the same canonical skill are rejected rather than silently overwritten.
"""

import csv
import json
import math
import warnings
from pathlib import Path

from match import _canonical_skill, _load_aliases
from scripts.build_roles import load_role_data as _load_role_data_from_csv


DATA_DIR = Path(__file__).resolve().parent / "data"


def load_role_data(data_dir=None):
    """Load role data, preferring the authoritative roles CSV.

    The CSV loader understands UTF-8 BOMs and parses the JSON skill columns.
    Generated JSON is a fallback for copied data folders without a CSV.
    """
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    csv_path = directory / "roles.csv"
    if csv_path.is_file():
        return _load_role_data_from_csv(csv_path)

    catalogue_path = directory / "roles_catalogue.json"
    if catalogue_path.is_file():
        with catalogue_path.open(encoding="utf-8") as source:
            roles = json.load(source)

        def read_optional_json(filename, default):
            path = directory / filename
            if not path.is_file():
                return default
            with path.open(encoding="utf-8") as source:
                return json.load(source)

        return {
            "roles": roles,
            "role_weights": read_optional_json("role_weights.json", {}),
            "role_sources": read_optional_json("role_sources.json", {}),
            "role_descriptions": read_optional_json("role_descriptions.json", {}),
        }

    legacy_path = directory / "roles.json"
    if legacy_path.is_file():
        with legacy_path.open(encoding="utf-8") as source:
            roles = json.load(source)
        return {
            "roles": roles,
            "role_weights": {},
            "role_sources": {},
            "role_descriptions": {},
        }

    raise FileNotFoundError(
        f"No roles.csv, roles_catalogue.json, or roles.json found in {directory}."
    )


def _number(value, label, *, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number.") from exc
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"{label} must be finite" + (" and positive." if positive else "."))
    return number


def get_weights(scenario_name, *, data_dir=None):
    """Return canonical skill weights; data_dir supports isolated data copies.

    All catalogue skills default to the configured neutral weight. Non-catalogue
    trend skills are also returned; match.score_roles ignores irrelevant skills.
    Explicit is_scenario_input=false rows are excluded. Missing flags are allowed.
    Uncertain active trends stay neutral in every scenario. Synthetic inputs emit
    a warning; evidence is not independently verified here.
    """
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    with (directory / "scenario_settings.json").open(encoding="utf-8") as source:
        settings = json.load(source)
    if scenario_name not in settings["scenarios"]:
        raise ValueError(f"Unknown scenario {scenario_name!r}; choose moderate or fast_disruption.")
    multipliers = settings["scenarios"][scenario_name]
    neutral = _number(settings["neutral_weight"], "neutral_weight", positive=True)
    minimum = _number(settings["minimum_weight"], "minimum_weight", positive=True)
    sensitivity = _number(settings["growth_rate_sensitivity"], "growth_rate_sensitivity")
    limit = _number(settings["growth_adjustment_limit"], "growth_adjustment_limit")
    if sensitivity < 0 or not 0 <= limit < 1:
        raise ValueError("Growth sensitivity must be nonnegative and adjustment limit in [0, 1).")
    factors = {
        direction: _number(multipliers[direction], direction, positive=True)
        for direction in ("rising", "stable", "declining")
    }
    if not factors["declining"] < factors["stable"] == neutral < factors["rising"]:
        raise ValueError("Multipliers must satisfy declining < stable = neutral < rising.")
    aliases_path = directory / "skill_aliases.json"
    aliases = (
        _load_aliases(directory)
        if aliases_path.is_file()
        else _load_aliases()
    )
    roles = load_role_data(directory)["roles"]
    weights = {
        _canonical_skill(skill, aliases): neutral
        for required in roles.values()
        for skill in ([required] if isinstance(required, str) else required)
    }
    trends_path = directory / "trends.csv"
    if not trends_path.exists():
        warnings.warn("No trends.csv found; returning neutral weights.", UserWarning, stacklevel=2)
        return weights

    seen = {}
    synthetic = False
    with trends_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"skill_name", "trend_direction"}.issubset(reader.fieldnames or []):
            raise ValueError("trends.csv requires skill_name and trend_direction headers.")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV row at line {reader.line_num}.")
            flag = row.get("is_scenario_input", "").strip().lower()
            if flag == "false":
                continue
            if flag not in ("", "true"):
                raise ValueError("is_scenario_input must be true, false, or empty.")
            skill = _canonical_skill(row["skill_name"], aliases)
            direction = row["trend_direction"].strip().lower()
            if not skill or direction not in {*factors, "uncertain"}:
                raise ValueError(f"Invalid skill or trend_direction at line {reader.line_num}.")
            raw_growth = row.get("growth_rate", "").strip().removesuffix("%")
            growth = _number(raw_growth, "growth_rate") if raw_growth else 0.0
            signature = (direction, growth)
            if skill in seen and seen[skill] != signature:
                raise ValueError(f"Conflicting trends for {skill!r}; resolve them before scoring.")
            seen[skill] = signature
            if direction == "uncertain":
                # Uncertainty is evidence metadata, not a score signal.
                weight = neutral
            else:
                adjustment = max(-limit, min(limit, growth * sensitivity))
                # Stable stays neutral; growth reinforces direction without
                # crossing neutral in the opposite direction.
                weight = factors[direction] * (1 + adjustment)
                if direction == "stable":
                    weight = neutral
                elif direction == "rising":
                    weight = max(factors[direction], weight)
                else:
                    weight = min(factors[direction], weight)
            weights[skill] = max(minimum, weight)
            synthetic |= "synthetic" in row.get("verification_status", "").lower()
    if synthetic:
        warnings.warn("Synthetic trends: test estimates, not verified evidence.", UserWarning, stacklevel=2)
    return weights