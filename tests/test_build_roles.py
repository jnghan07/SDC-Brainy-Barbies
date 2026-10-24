"""Check role CSV conversion using temporary files only."""

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_roles.py"
SPEC = importlib.util.spec_from_file_location("build_roles", SCRIPT_PATH)
build_roles_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_roles_module)


class BuildRolesTests(unittest.TestCase):
    """Exercise the builder without reading or writing the project's data folder."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name)
        self.csv_path = self.data_dir / "roles.csv"
        self.fields = [
            "role_id",
            "role_name",
            "role_description",
            "required_skills",
            "skill_weights",
            "occupation_source",
            "source_url",
            "verification_status",
            "record_notes",
        ]
        self.rows = [
            {
                "role_id": "TEST-001",
                "role_name": "Role One",
                "role_description": "Description for Role One",
                "required_skills": json.dumps([" Python ", "Data Analysis"]),
                "skill_weights": json.dumps({"Python": 3, "Data Analysis": 2}),
                "occupation_source": "Source A",
                "source_url": "https://example.test/a",
                "verification_status": "verified",
                "record_notes": (
                    "Content was inspected, but direct access returned HTTP 403. "
                    "The exact skill mapping remains for review."
                ),
            },
            {
                "role_id": "TEST-002",
                "role_name": "Role Two",
                "role_description": "Description for Role Two",
                "required_skills": json.dumps(["Git"]),
                "skill_weights": json.dumps({"Git": 1}),
                "occupation_source": "",
                "source_url": "",
                "verification_status": "",
            },
            {
                "role_id": "TEST-003",
                "role_name": "Role Three",
                "role_description": "Description for Role Three",
                "required_skills": json.dumps(["Testing", "Python"]),
                # Deliberately missing Python's weight.
                "skill_weights": json.dumps({"Testing": 2}),
                "occupation_source": "Source C",
                "source_url": "https://example.test/c",
                "verification_status": "candidate",
            },
        ]
        self.write_csv()

    def write_csv(self):
        """Write the small fixture inside this test's temporary folder."""
        with self.csv_path.open("w", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=self.fields)
            writer.writeheader()
            writer.writerows(self.rows)

    def test_good_rows_convert_and_bad_row_raises(self):
        """The two valid rows normalize, while the deliberately wrong row fails."""
        with self.csv_path.open(newline="", encoding="utf-8") as input_file:
            csv_rows = list(csv.DictReader(input_file))

        first = build_roles_module.convert_role_row(csv_rows[0], 2)
        self.assertEqual(first["role_name"], "Role One")
        self.assertEqual(first["required_skills"], ["python", "data analysis"])
        self.assertEqual(
            first["skill_weights"],
            {"python": 3, "data analysis": 2},
        )
        self.assertEqual(first["sources"]["role_id"], "TEST-001")
        self.assertEqual(
            first["sources"]["verification_notes"],
            self.rows[0]["record_notes"],
        )
        self.assertEqual(
            first["sources"]["source_url"],
            "https://example.test/a",
        )
        self.assertEqual(
            set(first["sources"]),
            {
                "role_id",
                "occupation_source",
                "source_url",
                "verification_status",
                "verification_notes",
            },
        )
        self.assertNotIn("supplemental_sources", first["sources"])
        self.assertIsInstance(first["sources"]["source_url"], str)

        second = build_roles_module.convert_role_row(csv_rows[1], 3)
        self.assertEqual(second["required_skills"], ["git"])
        self.assertEqual(second["skill_weights"], {"git": 1})
        self.assertIsNone(second["sources"]["occupation_source"])
        self.assertIsNone(second["sources"]["source_url"])
        self.assertIsNone(second["sources"]["verification_status"])
        self.assertNotIn("verification_notes", second["sources"])

        with self.assertRaisesRegex(ValueError, "keys must exactly match"):
            build_roles_module.convert_role_row(csv_rows[2], 4)
        with self.assertRaisesRegex(ValueError, "keys must exactly match"):
            build_roles_module.load_roles(self.csv_path)

        self.assertEqual(list(self.data_dir.iterdir()), [self.csv_path])

    def test_valid_temporary_csv_writes_expected_json_files(self):
        """A corrected temporary fixture writes all generated role structures."""
        self.rows[2]["skill_weights"] = json.dumps({"Testing": 2, "Python": 1})
        self.write_csv()

        build_roles_module.build_roles(self.data_dir)

        catalogue = json.loads(
            (self.data_dir / "roles_catalogue.json").read_text(encoding="utf-8")
        )
        weights = json.loads(
            (self.data_dir / "role_weights.json").read_text(encoding="utf-8")
        )
        sources = json.loads(
            (self.data_dir / "role_sources.json").read_text(encoding="utf-8")
        )
        self.assertEqual(catalogue["Role One"], ["python", "data analysis"])
        self.assertEqual(weights["Role Three"], {"testing": 2, "python": 1})
        self.assertEqual(
            sources["Role Two"],
            {
                "role_id": "TEST-002",
                "occupation_source": None,
                "source_url": None,
                "verification_status": None,
            },
        )
        self.assertNotIn("supplemental_sources", sources["Role One"])
        self.assertIsInstance(sources["Role One"]["source_url"], str)
        self.assertTrue(
            all(
                isinstance(source["source_url"], str)
                for source in sources.values()
                if source["source_url"] is not None
            )
        )
        self.assertEqual(
            sources["Role One"]["verification_notes"],
            self.rows[0]["record_notes"],
        )
        self.assertEqual(
            json.loads((self.data_dir / "roles.json").read_text(encoding="utf-8")),
            catalogue,
        )
        self.assertEqual(
            json.loads(
                (self.data_dir / "role_descriptions.json").read_text(
                    encoding="utf-8"
                )
            ),
            {
                "Role One": "Description for Role One",
                "Role Two": "Description for Role Two",
                "Role Three": "Description for Role Three",
            },
        )

    def test_bom_prefixed_csv_header_loads_and_maps_role_description(self):
        with self.csv_path.open("w", newline="", encoding="utf-8-sig") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=self.fields)
            writer.writeheader()
            writer.writerows(self.rows[:1])

        data = build_roles_module.load_role_data(self.csv_path)
        self.assertEqual(list(data["roles"]), ["Role One"])
        self.assertEqual(
            data["role_descriptions"]["Role One"],
            "Description for Role One",
        )
        self.assertEqual(
            data["role_sources"]["Role One"]["role_id"],
            "TEST-001",
        )


if __name__ == "__main__":
    unittest.main()
