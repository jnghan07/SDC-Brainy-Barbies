"""Compare neutral, moderate, and fast scenario scores using project data."""

import csv
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match import canonical_skill, load_aliases, score_roles
from scenarios import get_weights, load_role_data


DATA_DIR = ROOT / "data"
PROFILES_PATH = ROOT / "tests" / "test_profiles.json"
ROLES_PATH = DATA_DIR / "roles.csv"
SETTINGS_PATH = DATA_DIR / "scenario_settings.json"
TRENDS_PATH = DATA_DIR / "trends.csv"


def read_json(path):
    """Read one JSON file from the project."""
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def score_by_role(
    skills,
    roles,
    weights=None,
    skills_to_ignore=None,
    role_weights=None,
):
    """Make a role-to-score lookup from the matcher's results."""
    if weights is None:
        results = score_roles(
            skills,
            roles,
            skills_to_ignore=skills_to_ignore,
            role_weights=role_weights,
        )
    else:
        results = score_roles(
            skills,
            roles,
            weights=weights,
            skills_to_ignore=skills_to_ignore,
            role_weights=role_weights,
        )
    return {result["role"]: result for result in results}


def print_table(headers, rows):
    """Print aligned columns using only the standard library."""
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def read_trends():
    """Return trend rows, column names, and normalized active directions."""
    if not TRENDS_PATH.is_file():
        return None, set(), {}

    aliases = load_aliases()
    with TRENDS_PATH.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = set(reader.fieldnames or [])
        rows = list(reader)

    directions = {}
    for row in rows:
        skill_name = row.get("skill_name", "")
        direction = row.get("trend_direction", "").strip().lower()
        if row.get("is_scenario_input", "").strip().lower() == "false":
            continue
        if skill_name and direction:
            directions[canonical_skill(skill_name, aliases)] = direction

    return rows, fieldnames, directions


def ranking(results, role_names):
    """Return role names ordered by their score, preserving input order for ties."""
    return sorted(role_names, key=lambda role: results[role]["score"], reverse=True)


def main():
    """Load the inputs, print score comparisons, and summarize findings."""
    required_paths = [PROFILES_PATH, ROLES_PATH, SETTINGS_PATH]
    missing_paths = [path for path in required_paths if not path.is_file()]
    if missing_paths:
        for path in missing_paths:
            print(f"Missing required file: {path.relative_to(ROOT)}")
        return 1

    role_data = load_role_data(DATA_DIR)
    roles = role_data["roles"]
    role_weights = role_data["role_weights"]
    profiles = read_json(PROFILES_PATH)["profiles"]
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        moderate_weights = get_weights("moderate")
        fast_weights = get_weights("fast_disruption")

    headers = [
        "profile",
        "role",
        "neutral score",
        "moderate score",
        "fast score",
        "moderate (claimed-only ignored)",
        "fast (claimed-only ignored)",
    ]
    table_rows = []
    analyses = []
    all_scores = []

    # Collect each profile's neutral and scenario scores for comparison.
    for profile in profiles:
        profile_id = profile["id"]
        skills = profile.get("skills", [])
        claimed_only = profile.get("claimed_only", [])
        neutral = score_by_role(
            skills, roles, role_weights=role_weights
        )
        moderate = score_by_role(
            skills, roles, moderate_weights, role_weights=role_weights
        )
        fast = score_by_role(
            skills, roles, fast_weights, role_weights=role_weights
        )
        moderate_evidenced = None
        fast_evidenced = None

        if claimed_only:
            moderate_evidenced = score_by_role(
                skills,
                roles,
                moderate_weights,
                skills_to_ignore=claimed_only,
                role_weights=role_weights,
            )
            fast_evidenced = score_by_role(
                skills,
                roles,
                fast_weights,
                skills_to_ignore=claimed_only,
                role_weights=role_weights,
            )

        for role_name in roles:
            neutral_score = neutral[role_name]["score"]
            moderate_score = moderate[role_name]["score"]
            fast_score = fast[role_name]["score"]
            moderate_evidenced_score = (
                moderate_evidenced[role_name]["score"]
                if moderate_evidenced is not None
                else "—"
            )
            fast_evidenced_score = (
                fast_evidenced[role_name]["score"]
                if fast_evidenced is not None
                else "—"
            )
            table_rows.append(
                [
                    profile_id,
                    role_name,
                    neutral_score,
                    moderate_score,
                    fast_score,
                    moderate_evidenced_score,
                    fast_evidenced_score,
                ]
            )
            all_scores.extend(
                [
                    (f"{profile_id}, {role_name}, neutral", neutral_score),
                    (f"{profile_id}, {role_name}, moderate", moderate_score),
                    (f"{profile_id}, {role_name}, fast", fast_score),
                ]
            )
            if moderate_evidenced is not None:
                all_scores.extend(
                    [
                        (
                            f"{profile_id}, {role_name}, moderate evidenced-only",
                            moderate_evidenced_score,
                        ),
                        (
                            f"{profile_id}, {role_name}, fast evidenced-only",
                            fast_evidenced_score,
                        ),
                    ]
                )

        analyses.append(
            {
                "id": profile_id,
                "neutral": neutral,
                "moderate": moderate,
                "fast": fast,
                "moderate_evidenced": moderate_evidenced,
                "fast_evidenced": fast_evidenced,
            }
        )

    print("Scores by profile and role")
    print_table(headers, table_rows)

    # Print all available trend rows and report whether source/date are present.
    trend_rows, trend_columns, trend_directions = read_trends()
    print("\nSkills in data/trends.csv and their trend directions")
    if trend_rows is None:
        print("data/trends.csv is missing; no trend rows are available.")
        print("Source column: cannot check (file missing). Date column: cannot check (file missing).")
    else:
        if trend_rows:
            for row in trend_rows:
                print(
                    f"{row.get('skill_name', '')}: "
                    f"{row.get('trend_direction', '')}"
                )
        else:
            print("No skill rows found.")
        print(f"Source column: {'yes' if 'source' in trend_columns else 'no'}.")
        print(f"Date column: {'yes' if 'date' in trend_columns else 'no'}.")

    # List every moderate-to-fast score difference, including evidenced-only scores.
    score_changes = []
    for analysis in analyses:
        for role_name in roles:
            neutral_result = analysis["moderate"][role_name]
            moderate_score = neutral_result["score"]
            fast_score = analysis["fast"][role_name]["score"]
            if moderate_score != fast_score:
                score_changes.append(
                    f"{analysis['id']} / {role_name}: "
                    f"moderate {moderate_score} -> fast {fast_score}"
                )

            if analysis["moderate_evidenced"] is not None:
                moderate_score = analysis["moderate_evidenced"][role_name]["score"]
                fast_score = analysis["fast_evidenced"][role_name]["score"]
                if moderate_score != fast_score:
                    score_changes.append(
                        f"{analysis['id']} evidenced-only / {role_name}: "
                        f"moderate {moderate_score} -> fast {fast_score}"
                    )

    print("\nAnswers")
    if score_changes:
        print("Moderate and fast scores that differ:")
        for change in score_changes:
            print(f"- {change}")
    else:
        print("Moderate vs fast: no scores change.")

    out_of_range = [
        (label, score)
        for label, score in all_scores
        if score < 0 or score > 100
    ]
    if out_of_range:
        print("Scores outside 0-100:")
        for label, score in out_of_range:
            print(f"- {label}: {score}")
    else:
        print("Scores outside 0-100: none.")

    # Compare scenario scores with the neutral result for matched trend skills.
    rising_examples = []
    declining_examples = []
    if trend_rows is not None:
        for analysis in analyses:
            for role_name in roles:
                neutral_result = analysis["neutral"][role_name]
                matched_skills = neutral_result["skills_have"]
                for scenario_name in ("moderate", "fast"):
                    scenario_result = analysis[scenario_name][role_name]
                    scenario_score = scenario_result["score"]
                    neutral_score = neutral_result["score"]
                    for skill in matched_skills:
                        direction = trend_directions.get(skill)
                        example = (
                            f"{analysis['id']} / {role_name}: "
                            f"{neutral_score} neutral -> {scenario_score} "
                            f"{scenario_name}; matched {direction} skill {skill}"
                        )
                        if direction == "rising" and scenario_score > neutral_score:
                            rising_examples.append(example)
                        elif direction == "declining" and scenario_score < neutral_score:
                            declining_examples.append(example)

    if trend_rows is None:
        print("Rising/declining comparison: cannot assess because data/trends.csv is missing.")
    else:
        if rising_examples:
            print(f"Rising skill raises score: {rising_examples[0]}.")
        else:
            print("Rising skill raises score: no matching example found.")
        if declining_examples:
            print(f"Declining skill lowers score: {declining_examples[0]}.")
        else:
            print("Declining skill lowers score: no matching example found.")

    rank_changes = []
    role_names = list(roles)
    for analysis in analyses:
        moderate_order = ranking(analysis["moderate"], role_names)
        fast_order = ranking(analysis["fast"], role_names)
        if moderate_order != fast_order:
            rank_changes.append(
                f"{analysis['id']}: moderate [{', '.join(moderate_order)}] "
                f"-> fast [{', '.join(fast_order)}]"
            )
    if rank_changes:
        print("Role ranking changes between moderate and fast:")
        for change in rank_changes:
            print(f"- {change}")
    else:
        print("Role ranking between moderate and fast: no changes.")

    notes = list(dict.fromkeys(str(item.message) for item in captured_warnings))
    if trend_rows is None:
        notes.append(
            "Without trends.csv, get_weights returns neutral weights for both scenarios."
        )
    if notes:
        print("Potentially surprising findings:")
        for note in dict.fromkeys(notes):
            print(f"- {note}")
    else:
        print("Potentially surprising findings: none.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
