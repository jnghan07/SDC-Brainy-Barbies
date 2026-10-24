"""Build normalized role data files from the authoritative data/roles.csv."""

import csv
import json
import sys
from pathlib import Path


# Find the project folder from this script, not from the current working folder.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"


def normalise_skill(skill):
    """Trim a skill name and make it lowercase."""
    return skill.strip().lower()


def convert_role_row(row, row_number):
    """Check one CSV row and return its normalized role data."""
    role_id = (row.get("role_id") or "").strip()
    role_name = (row.get("role_name") or "").strip()
    role_description = (row.get("role_description") or "").strip()

    # The two skill columns contain JSON text, so read them as JSON values.
    try:
        required_skills = json.loads(row.get("required_skills") or "")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            f"Row {row_number}: required_skills is not valid JSON: {error}"
        ) from error

    try:
        skill_weights = json.loads(row.get("skill_weights") or "")
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(
            f"Row {row_number}: skill_weights is not valid JSON: {error}"
        ) from error

    if not isinstance(required_skills, list) or any(
        not isinstance(skill, str) for skill in required_skills
    ):
        raise ValueError(
            f"Row {row_number}: required_skills must be a JSON list of strings."
        )
    if not isinstance(skill_weights, dict) or any(
        not isinstance(skill, str) for skill in skill_weights
    ):
        raise ValueError(
            f"Row {row_number}: skill_weights must be a JSON object with skill names."
        )

    # Normalize both sides before checking that each required skill has one weight.
    required = [normalise_skill(skill) for skill in required_skills]
    weights_by_skill = {}
    for skill, weight in skill_weights.items():
        normalized_skill = normalise_skill(skill)
        if normalized_skill in weights_by_skill:
            raise ValueError(
                f"Row {row_number} ({role_name or 'unnamed role'}): "
                f"more than one weight key normalizes to {normalized_skill!r}."
            )
        weights_by_skill[normalized_skill] = weight
    if set(weights_by_skill) != set(required):
        raise ValueError(
            f"Row {row_number} ({role_name or 'unnamed role'}): "
            "skill weight keys must exactly match required skills."
        )

    # Weights must be whole JSON numbers from 1 through 3.
    normalized_weights = {}
    for skill, weight in weights_by_skill.items():
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or weight not in (1, 2, 3)
        ):
            raise ValueError(
                f"Row {row_number} ({role_name or 'unnamed role'}): "
                f"weight for {skill!r} must be a whole number from 1 to 3."
            )
        normalized_weights[skill] = int(weight)

    # Keep source fields as null when the CSV cell is empty.
    sources = {}
    for field in (
        "role_id",
        "occupation_source",
        "source_url",
        "verification_status",
    ):
        value = row.get(field)
        sources[field] = value.strip() if value and value.strip() else None

    # Keep primary-source cautions available to readers of the generated JSON.
    # Older CSV files without notes still produce the same source structure.
    record_notes = (row.get("record_notes") or "").strip()
    if record_notes:
        sources["verification_notes"] = record_notes

    return {
        "role_id": role_id,
        "role_name": role_name,
        "role_description": role_description,
        "required_skills": required,
        "skill_weights": normalized_weights,
        "sources": sources,
    }


def load_role_data(csv_path):
    """Read and validate catalogue, weights, sources, and descriptions from CSV."""
    catalogue = {}
    role_weights = {}
    role_sources = {}
    role_descriptions = {}
    seen_ids = set()
    seen_names = set()

    try:
        source_file = Path(csv_path).open(newline="", encoding="utf-8-sig")
    except OSError as error:
        raise ValueError(f"Could not open roles CSV {csv_path}: {error}") from error

    with source_file:
        reader = csv.DictReader(source_file)
        required_columns = {
            "role_id",
            "role_name",
            "role_description",
            "required_skills",
            "skill_weights",
            "occupation_source",
            "source_url",
            "verification_status",
        }
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Roles CSV is missing required columns: {missing}.")

        for row_number, row in enumerate(reader, start=2):
            role = convert_role_row(row, row_number)
            role_id = role["role_id"]
            role_name = role["role_name"]
            normalized_name = role_name.casefold()

            if role_id and role_id in seen_ids:
                raise ValueError(f"Row {row_number}: duplicate role ID {role_id!r}.")
            if normalized_name in seen_names:
                raise ValueError(f"Row {row_number}: duplicate role name {role_name!r}.")

            if role_id:
                seen_ids.add(role_id)
            seen_names.add(normalized_name)

            catalogue[role_name] = role["required_skills"]
            role_weights[role_name] = role["skill_weights"]
            role_sources[role_name] = role["sources"]
            role_descriptions[role_name] = role["role_description"] or None

    return {
        "roles": catalogue,
        "role_weights": role_weights,
        "role_sources": role_sources,
        "role_descriptions": role_descriptions,
    }


def load_roles(csv_path):
    """Keep the original three-value loader interface for existing callers."""
    data = load_role_data(csv_path)
    return data["roles"], data["role_weights"], data["role_sources"]


def write_json(path, data):
    """Write one output file in readable UTF-8 JSON."""
    with Path(path).open("w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")


def print_report(catalogue, role_sources):
    """Print a summary of the generated roles and their skills."""
    print(f"Number of roles: {len(catalogue)}")

    no_source_url = [
        role for role, source in role_sources.items() if not source["source_url"]
    ]
    print(f"Roles with no source URL: {no_source_url}")

    fewer_than_three = [
        role for role, skills in catalogue.items() if len(skills) < 3
    ]
    print(f"Roles with fewer than 3 required skills: {fewer_than_three}")

    names_with_slash = [role for role in catalogue if "/" in role]
    print(f"Role names containing a slash: {names_with_slash}")

    # Count a role once for a skill, even if the CSV repeats that skill.
    roles_per_skill = {}
    for skills in catalogue.values():
        for skill in set(skills):
            roles_per_skill[skill] = roles_per_skill.get(skill, 0) + 1

    print("Distinct skills and number of roles that need each:")
    for skill in sorted(roles_per_skill):
        print(f"  {skill}: {roles_per_skill[skill]}")


def build_roles(data_dir=DATA_DIR):
    """Build role files from CSV; roles.json remains a synchronized compatibility copy."""
    data_dir = Path(data_dir)
    data = load_role_data(data_dir / "roles.csv")

    # Validate every row before writing any output file.
    write_json(data_dir / "roles_catalogue.json", data["roles"])
    write_json(data_dir / "roles.json", data["roles"])
    write_json(data_dir / "role_weights.json", data["role_weights"])
    write_json(data_dir / "role_sources.json", data["role_sources"])
    write_json(data_dir / "role_descriptions.json", data["role_descriptions"])
    print_report(data["roles"], data["role_sources"])


def main():
    """Run the builder and show clear errors to the user."""
    try:
        build_roles(DATA_DIR)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
