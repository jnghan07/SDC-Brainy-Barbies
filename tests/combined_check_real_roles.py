"""Compare neutral and scenario scores for the real role catalogue."""

import json
import shutil
import sys
import tempfile
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match import score_roles
from scenarios import get_weights


DATA_DIR = ROOT / "data"
PROFILE_SKILLS = [
    "statistics",
    "data visualization",
    "software development",
    "communication",
]


def read_json(path):
    """Read JSON from a project data file."""
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def copy_scenario_data(temporary_dir):
    """Copy current scenario inputs into the temporary folder."""
    temporary_dir = Path(temporary_dir)
    for filename in ("skill_aliases.json", "scenario_settings.json"):
        shutil.copyfile(DATA_DIR / filename, temporary_dir / filename)

    shutil.copyfile(
        DATA_DIR / "roles_catalogue.json",
        temporary_dir / "roles.json",
    )
    temporary_trends = temporary_dir / "trends.csv"
    shutil.copyfile(DATA_DIR / "trends.csv", temporary_trends)


def by_role(results):
    """Make it easy to look up a score and tier by role name."""
    return {result["role"]: result for result in results}


def print_table(headers, rows):
    """Print a plain aligned table using only the standard library."""
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


def main():
    """Calculate the three rankings and remove the temporary data copy."""
    roles = read_json(DATA_DIR / "roles_catalogue.json")
    role_weights = read_json(DATA_DIR / "role_weights.json")

    with tempfile.TemporaryDirectory(prefix="real-role-scenarios-") as temporary:
        temporary_dir = Path(temporary)
        copy_scenario_data(temporary_dir)

        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            weights_moderate = get_weights("moderate", data_dir=temporary_dir)
            weights_fast = get_weights("fast_disruption", data_dir=temporary_dir)

        neutral_results = by_role(
            score_roles(
                PROFILE_SKILLS,
                roles,
                role_weights=role_weights,
            )
        )
        moderate_results = by_role(
            score_roles(
                PROFILE_SKILLS,
                roles,
                weights=weights_moderate,
                role_weights=role_weights,
            )
        )
        fast_results = by_role(
            score_roles(
                PROFILE_SKILLS,
                roles,
                weights=weights_fast,
                role_weights=role_weights,
            )
        )

        # Neutral results are already ranked from highest score to lowest.
        ranked_roles = [
            result["role"]
            for result in sorted(
                neutral_results.values(),
                key=lambda result: result["score"],
                reverse=True,
            )
        ]
        table_rows = [
            (
                role,
                f'{neutral_results[role]["score"]} ({neutral_results[role]["tier"]})',
                f'{moderate_results[role]["score"]} ({moderate_results[role]["tier"]})',
                f'{fast_results[role]["score"]} ({fast_results[role]["tier"]})',
            )
            for role in ranked_roles
        ]

        print("Profile skills: " + ", ".join(PROFILE_SKILLS))
        print_table(
            [
                "Role",
                "Neutral score (tier)",
                "Moderate score (tier)",
                "Fast score (tier)",
            ],
            table_rows,
        )

        print("\nWarnings:")
        if captured_warnings:
            for warning in captured_warnings:
                print(f"- {warning.message}")
        else:
            print("None")

    print("Temporary folder removed: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
