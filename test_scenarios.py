"""Synthetic trend tests, not evidence of real labour-market ranking changes."""

import csv
import json
import shutil
import tempfile
import unittest
import warnings
from pathlib import Path

from match import canonical_skill, load_aliases, score_roles
from scenarios import DATA_DIR, get_weights, load_role_data


# User-provided illustrative directions; deliberately never saved in data/.
SYNTHETIC_TRENDS = [
    ("Python", "rising"),
    ("SQL", "stable"),
    ("Data Visualization", "rising"),
    ("Git", "stable"),
    ("Figma", "declining"),
    ("User Research", "rising"),
]


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        for name in ("scenario_settings.json",):
            shutil.copyfile(DATA_DIR / name, self.directory / name)
        # Keep this small synthetic fixture stable as the production role
        # catalogue changes independently.
        self.roles = {
            "Junior Software Engineer": [
                "python",
                "git",
                "sql",
                "testing",
                "ai-assisted coding",
            ],
            "Data Analyst": [
                "python",
                "sql",
                "statistics",
                "data visualisation",
            ],
            "UX Designer": [
                "figma",
                "user research",
                "prototyping",
                "html",
                "css",
            ],
        }
        (self.directory / "roles.json").write_text(
            json.dumps(self.roles),
            encoding="utf-8",
        )
        self.rows = [
            {
                "skill_name": skill,
                "trend_direction": direction,
                "growth_rate": "",
                "verification_status": "synthetic_unverified",
                "is_scenario_input": "true",
                "evidence_summary": "Synthetic test assumption, not verified evidence.",
            }
            for skill, direction in SYNTHETIC_TRENDS
        ]
        self.write_trends()

    def write_trends(self):
        with (self.directory / "trends.csv").open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=list(self.rows[0]))
            writer.writeheader()
            writer.writerows(self.rows)

    def weights(self, scenario="moderate"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return get_weights(scenario, data_dir=self.directory)

    def test_editing_temporary_trend_changes_weight_and_role_score(self):
        before = self.weights()
        self.rows[0]["trend_direction"] = "declining"
        self.write_trends()
        after = self.weights()
        self.assertGreater(before["python"], after["python"])
        def analyst_score(weights):
            return next(
                result["score"]
                for result in score_roles(["python"], self.roles, weights=weights)
                if result["role"] == "Data Analyst"
            )
        self.assertGreater(analyst_score(before), analyst_score(after))

    def test_synthetic_scenarios_change_ranking_without_a_tie(self):
        profile = ["css", "sql"]
        moderate = score_roles(profile, self.roles, weights=self.weights())
        fast = score_roles(profile, self.roles, weights=self.weights("fast_disruption"))
        self.assertEqual(moderate[0]["role"], "Data Analyst")
        self.assertEqual(fast[0]["role"], "UX Designer")
        for ranking in (moderate, fast):
            self.assertGreater(ranking[0]["score"], ranking[1]["score"])

    def test_direction_aliases_and_missing_skill_defaults(self):
        weights = self.weights()
        self.assertGreater(weights["python"], 1.0)
        self.assertEqual(weights["sql"], 1.0)
        self.assertLess(weights["figma"], 1.0)
        self.assertEqual(weights["testing"], 1.0)
        self.assertGreater(weights["data visualisation"], 1.0)
        self.assertNotIn("data visualization", weights)

    def test_uncertain_active_trend_stays_neutral_in_every_scenario(self):
        self.rows[0]["trend_direction"] = "uncertain"
        self.rows[0]["growth_rate"] = "999999"
        self.write_trends()

        self.assertEqual(self.weights("moderate")["python"], 1.0)
        self.assertEqual(self.weights("fast_disruption")["python"], 1.0)

    def test_missing_file_and_header_only_are_neutral(self):
        self.rows = []
        (self.directory / "trends.csv").write_text("skill_name,trend_direction\n")
        self.assertTrue(all(weight == 1.0 for weight in self.weights().values()))
        (self.directory / "trends.csv").unlink()
        with self.assertWarnsRegex(UserWarning, "neutral"):
            weights = get_weights("moderate", data_dir=self.directory)
        self.assertTrue(all(weight == 1.0 for weight in weights.values()))
        self.assertEqual(weights, self.weights("fast_disruption"))

    def test_optional_growth_adjustment_is_bounded_and_stable_stays_neutral(self):
        before = self.weights()
        self.rows[0]["growth_rate"] = "10%"
        self.rows[1]["growth_rate"] = "10"
        self.rows[4]["growth_rate"] = "-10"
        self.write_trends()
        after = self.weights()
        self.assertAlmostEqual(after["python"], 1.26)
        self.assertEqual(after["sql"], 1.0)
        self.assertLess(after["figma"], before["figma"])
        self.rows[0]["growth_rate"] = "999999"
        self.write_trends()
        self.assertAlmostEqual(self.weights()["python"], 1.32)

    def test_unknown_scenario_and_invalid_values_fail_explicitly(self):
        with self.assertRaises(ValueError):
            self.weights("unknown")
        self.rows[0]["trend_direction"] = "unknown"
        self.write_trends()
        with self.assertRaises(ValueError):
            self.weights()
        self.rows[0]["trend_direction"] = "rising"
        self.rows[0]["growth_rate"] = "NaN"
        self.write_trends()
        with self.assertRaises(ValueError):
            self.weights()

    def test_excluded_rows_and_conflicting_duplicates(self):
        self.rows[0]["is_scenario_input"] = "false"
        self.write_trends()
        self.assertEqual(self.weights()["python"], 1.0)
        self.rows[0]["is_scenario_input"] = "true"
        self.rows.append(dict(self.rows[0], trend_direction="declining"))
        self.write_trends()
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.weights()

    def test_synthetic_input_warns(self):
        with self.assertWarnsRegex(UserWarning, "Synthetic"):
            get_weights("moderate", data_dir=self.directory)

    def test_project_roles_trends_and_scorer_use_all_eleven_roles(self):
        role_data = load_role_data(DATA_DIR)
        roles = role_data["roles"]
        role_ids = {
            source["role_id"] for source in role_data["role_sources"].values()
        }
        self.assertEqual(len(roles), 11)
        self.assertEqual(len(role_data["role_weights"]), 11)
        self.assertEqual(len(role_data["role_descriptions"]), 11)
        self.assertEqual(
            json.loads((DATA_DIR / "roles_catalogue.json").read_text()),
            role_data["roles"],
        )
        self.assertEqual(
            json.loads((DATA_DIR / "roles.json").read_text()),
            role_data["roles"],
        )
        self.assertEqual(
            json.loads((DATA_DIR / "role_weights.json").read_text()),
            role_data["role_weights"],
        )
        self.assertEqual(
            json.loads((DATA_DIR / "role_sources.json").read_text()),
            role_data["role_sources"],
        )
        self.assertEqual(
            json.loads((DATA_DIR / "role_descriptions.json").read_text()),
            role_data["role_descriptions"],
        )

        with (DATA_DIR / "trends.csv").open(
            encoding="utf-8-sig", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 15)
        self.assertTrue(
            all(row["role_id"] in role_ids for row in rows)
        )
        self.assertTrue(
            all(
                row["trend_direction"] in {
                    "rising",
                    "stable",
                    "declining",
                    "uncertain",
                }
                for row in rows
            )
        )

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            moderate = get_weights("moderate")
            fast = get_weights("fast_disruption")
        self.assertEqual(captured, [])
        self.assertEqual(moderate["cybersecurity"], 1.2)
        self.assertEqual(fast["cybersecurity"], 2.0)
        self.assertEqual(moderate["ux design"], 1.0)
        self.assertEqual(fast["ux design"], 1.0)
        aliases = load_aliases()
        active_skills = {
            canonical_skill(row["skill_name"], aliases)
            for row in rows
            if row["is_scenario_input"].strip().lower() == "true"
        }
        context_skills = {
            canonical_skill(row["skill_name"], aliases)
            for row in rows
            if row["is_scenario_input"].strip().lower() == "false"
        }
        for skill in context_skills - active_skills:
            self.assertEqual(moderate.get(skill, 1.0), 1.0)
            self.assertEqual(fast.get(skill, 1.0), 1.0)

        all_skills = [
            skill
            for required in roles.values()
            for skill in required
        ]
        for scenario_weights in (moderate, fast):
            results = score_roles(
                all_skills,
                roles,
                weights=scenario_weights,
                role_weights=role_data["role_weights"],
            )
            self.assertEqual(len(results), 11)
            self.assertEqual({result["role"] for result in results}, set(roles))
            self.assertTrue(
                all(0 <= result["score"] <= 100 for result in results)
            )


if __name__ == "__main__":
    unittest.main()