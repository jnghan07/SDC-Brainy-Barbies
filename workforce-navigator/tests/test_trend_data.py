from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from modules.trend_data import (
    DatasetValidationError,
    canonicalize_skill,
    get_courses,
    get_role,
    get_role_skills,
    get_roles,
    get_scenario_inputs,
    get_sdg_mappings,
    get_trends,
    load_datasets,
    validate_datasets,
)
from scripts.update_data import plan_csv_update


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"


class StarterContractTests(unittest.TestCase):
    def test_starter_datasets_validate_and_have_expected_record_counts(self) -> None:
        result = validate_datasets()
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["record_counts"], {"roles": 10, "trends": 0, "courses": 0, "sdg_mappings": 2})

    def test_public_retrieval_contract(self) -> None:
        self.assertEqual(len(get_roles()), 10)
        self.assertEqual(get_role("MY-CAND-001")["role_name"], "Data Analyst")
        self.assertEqual(get_role_skills("MY-CAND-001"), ["Data Analysis", "SQL", "Python", "Data Visualization"])
        self.assertEqual(len(get_trends()), 0)
        self.assertEqual(len(get_courses()), 0)
        self.assertEqual(len(get_courses("ML")), 0)
        self.assertEqual(len(get_sdg_mappings("MY-CAND-006")), 2)
        scenario_inputs = get_scenario_inputs()
        self.assertTrue(scenario_inputs.empty)
        self.assertIn("proposed_scenario_adjustment", scenario_inputs.columns)

    def test_not_found_and_invalid_skill_behaviour(self) -> None:
        with self.assertRaisesRegex(KeyError, "Unknown role_id"):
            get_role("missing-role")
        with self.assertRaisesRegex(KeyError, "Unknown role_id"):
            get_trends("missing-role")
        with self.assertRaisesRegex(ValueError, "Unknown skill"):
            get_courses("Unlisted Skill")

    def test_aliases_normalize_to_canonical_vocabulary(self) -> None:
        self.assertEqual(canonicalize_skill(" ML "), "Machine Learning")
        self.assertEqual(canonicalize_skill("data visualisation"), "Data Visualization")


class FixtureValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        for name in ("roles", "trends", "courses", "sdg_mappings"):
            with (self.data_dir / f"{name}.csv").open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                if name == "roles":
                    writer.writerow(
                        [
                            "role_id", "role_name", "role_description", "required_skills", "skill_weights",
                            "occupation_source", "source_url", "verification_status", "record_notes",
                        ]
                    )
                    writer.writerow(
                        ["TEST-001", "Test role", "Candidate description", '["Python"]', "{}",
                         "", "", "candidate_unverified", "Fixture only"]
                    )
                elif name == "trends":
                    writer.writerow(
                        [
                            "trend_id", "role_id", "skill_name", "trend_direction", "evidence_summary",
                            "source_name", "source_url", "publication_date", "retrieved_date", "evidence_type",
                            "confidence_level", "verification_status", "is_scenario_input", "scenario_relevance",
                            "proposed_scenario_adjustment", "adjustment_basis", "interpretation_limitations",
                        ]
                    )
                    writer.writerow(
                        [
                            "FIXTURE-TREND-001", "TEST-001", "Python", "uncertain", "Fictional fixture evidence",
                            "Example source", "", "", "", "unknown", "not_assessed", "candidate_unverified",
                            "false", "", "", "", "",
                        ]
                    )
                elif name == "courses":
                    writer.writerow(
                        [
                            "course_id", "course_name", "provider", "target_skills", "course_url", "cost_status",
                            "availability_status", "last_verified_date", "source_url", "verification_status",
                            "record_notes",
                        ]
                    )
                    writer.writerow(
                        [
                            "FIXTURE-COURSE-001", "Fictional Example Course", "Example Provider",
                            '["Python"]', "https://example.com/course", "unknown", "available", "2025-01-01",
                            "https://example.com/source", "verified", "Fictional test fixture; not a real course claim",
                        ]
                    )
                else:
                    writer.writerow(
                        [
                            "role_id", "sdg_id", "sdg_name", "mapping_rationale", "supporting_evidence",
                            "source_url", "verification_status", "record_notes",
                        ]
                    )
                    writer.writerow(
                        [
                            "TEST-001", "12", "Responsible Consumption and Production",
                            "Fictional fixture rationale", "", "", "candidate_unverified", "Fixture only",
                        ]
                    )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_import(self, dataset: str, rows: list[dict[str, str]]) -> Path:
        with (self.data_dir / f"{dataset}.csv").open(newline="", encoding="utf-8") as file:
            columns = next(csv.reader(file))
        import_path = self.data_dir / f"incoming_{dataset}.csv"
        with import_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return import_path

    @staticmethod
    def _candidate_role(role_id: str, role_name: str) -> dict[str, str]:
        return {
            "role_id": role_id,
            "role_name": role_name,
            "role_description": "Fictional candidate record for importer testing.",
            "required_skills": '["Python"]',
            "skill_weights": "{}",
            "occupation_source": "",
            "source_url": "",
            "verification_status": "candidate_unverified",
            "record_notes": "Fictional test fixture only.",
        }

    def test_fixture_is_loadable_with_same_interface(self) -> None:
        result = validate_datasets(self.data_dir)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(get_role("TEST-001", data_dir=self.data_dir)["role_name"], "Test role")
        self.assertEqual(get_role_skills("TEST-001", data_dir=self.data_dir), ["Python"])
        self.assertEqual(len(get_trends("TEST-001", data_dir=self.data_dir)), 1)
        self.assertEqual(
            get_courses("Python", data_dir=self.data_dir)["course_id"].tolist(),
            ["FIXTURE-COURSE-001"],
        )
        self.assertEqual(len(get_sdg_mappings("TEST-001", data_dir=self.data_dir)), 1)
        self.assertEqual(set(load_datasets(self.data_dir)), {"roles", "trends", "courses", "sdg_mappings"})

    def test_missing_file_is_reported_and_raises_on_load(self) -> None:
        (self.data_dir / "courses.csv").unlink()
        result = validate_datasets(self.data_dir)
        self.assertFalse(result["valid"])
        self.assertTrue(any("Missing required dataset file" in item for item in result["errors"]))
        with self.assertRaises(DatasetValidationError):
            load_datasets(self.data_dir)

    def test_missing_required_column_is_actionable(self) -> None:
        role_file = self.data_dir / "roles.csv"
        content = role_file.read_text(encoding="utf-8")
        role_file.write_text(content.replace("role_description,", ""), encoding="utf-8")
        result = validate_datasets(self.data_dir)
        self.assertFalse(result["valid"])
        self.assertTrue(any("roles.csv is missing required columns: role_description" in item for item in result["errors"]))

    def test_duplicate_ids_invalid_dates_and_references_are_rejected(self) -> None:
        trend_file = self.data_dir / "trends.csv"
        with trend_file.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            row = [
                "DUP", "NO-SUCH-ROLE", "Python", "growing", "Evidence", "Example source",
                "https://example.com/report", "2025-02-30", "2025-03-01", "report", "high",
                "candidate_unverified", "false", "", "", "", "",
            ]
            writer.writerow(row)
            writer.writerow(row)
        result = validate_datasets(self.data_dir)
        self.assertFalse(result["valid"])
        joined = "\n".join(result["errors"])
        self.assertIn("duplicate trend_id", joined)
        self.assertIn("does not exist in roles.csv", joined)
        self.assertIn("invalid trend_direction", joined)
        self.assertIn("real ISO date", joined)

    def test_invalid_verification_value_is_rejected(self) -> None:
        role_file = self.data_dir / "roles.csv"
        content = role_file.read_text(encoding="utf-8").replace("candidate_unverified", "maybe")
        role_file.write_text(content, encoding="utf-8")
        result = validate_datasets(self.data_dir)
        self.assertFalse(result["valid"])
        self.assertTrue(any("verification_status must be one of" in item for item in result["errors"]))

    def test_update_dry_run_reports_candidate_review_without_writing(self) -> None:
        import_path = self._write_import("roles", [self._candidate_role("TEST-002", "Second test role")])
        report = plan_csv_update("roles", import_path, data_dir=self.data_dir)
        self.assertEqual(report["added"], 1)
        self.assertEqual(report["needs_review"], 1)
        self.assertFalse(report["applied"])
        self.assertEqual(len(get_roles(data_dir=self.data_dir)), 1)

    def test_update_apply_writes_only_valid_candidate_records(self) -> None:
        import_path = self._write_import("roles", [self._candidate_role("TEST-002", "Second test role")])
        report = plan_csv_update("roles", import_path, data_dir=self.data_dir, apply=True)
        self.assertEqual(report["added"], 1)
        self.assertTrue(report["applied"])
        self.assertEqual(len(get_roles(data_dir=self.data_dir)), 2)

    def test_unverified_import_never_replaces_verified_role(self) -> None:
        roles_path = self.data_dir / "roles.csv"
        with roles_path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            columns = reader.fieldnames
            verified_role = next(reader)
        verified_role["occupation_source"] = "Fictional example source"
        verified_role["source_url"] = "https://example.com/fictional-source"
        verified_role["verification_status"] = "verified"
        with roles_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerow(verified_role)
        incoming_role = self._candidate_role("TEST-001", "Changed unverified title")
        import_path = self._write_import("roles", [incoming_role])

        report = plan_csv_update("roles", import_path, data_dir=self.data_dir, apply=True)

        self.assertEqual(report["changed"], 0)
        self.assertEqual(report["needs_review"], 1)
        self.assertFalse(report["applied"])
        self.assertEqual(get_role("TEST-001", data_dir=self.data_dir)["role_name"], "Test role")

    def test_duplicate_import_keys_are_reported_not_silently_dropped(self) -> None:
        row = self._candidate_role("TEST-002", "Second test role")
        import_path = self._write_import("roles", [row, row])
        report = plan_csv_update("roles", import_path, data_dir=self.data_dir)
        self.assertEqual(report["added"], 1)
        self.assertEqual(report["rejected"], 1)
        self.assertIn("Duplicate key", report["rejections"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
