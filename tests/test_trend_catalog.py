"""Regression checks for the manually reviewed trend catalogue.

These checks enforce the data contract, not the truth of a source claim.
Evidence interpretation still requires review of the cited source sections.
"""

from __future__ import annotations

import csv
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from modules.trend_data import (
    CANONICAL_SKILLS,
    CONFIDENCE_LEVELS,
    EVIDENCE_TYPES,
    REQUIRED_COLUMNS,
    TREND_DIRECTIONS,
    VERIFICATION_STATUSES,
    get_roles,
    get_scenario_inputs,
    get_trends,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class TrendCatalogueTests(unittest.TestCase):
    def test_csv_is_nonempty_and_preserves_all_17_columns(self) -> None:
        with (DATA_DIR / "trends.csv").open(newline="", encoding="utf-8") as file:
            rows = list(csv.reader(file))
        self.assertEqual(tuple(rows[0]), REQUIRED_COLUMNS["trends"])
        self.assertEqual(len(rows[0]), 17)
        self.assertGreater(len(rows), 1, "The evidence deliverable must not regress to a header-only file.")
        for line, row in enumerate(rows[1:], start=2):
            with self.subTest(line=line):
                self.assertEqual(len(row), 17)

    def test_records_have_valid_references_and_canonical_labels(self) -> None:
        trends = get_trends()
        self.assertTrue(trends["trend_id"].is_unique)
        self.assertEqual(
            set(zip(trends["role_id"], trends["skill_name"])),
            {
                ("MY-CAND-001", "Data Analysis"),
                ("MY-CAND-010", "Machine Learning"),
                ("MY-CAND-003", "Cybersecurity"),
                ("MY-CAND-001", "Analytical Thinking"),
                ("MY-CAND-004", "UI/UX Design"),
            },
        )
        self.assertTrue(set(trends["role_id"]).issubset(set(get_roles()["role_id"])))
        self.assertTrue(set(trends["skill_name"]).issubset(CANONICAL_SKILLS))

    def test_evidence_metadata_is_complete_and_controlled(self) -> None:
        for row in get_trends().to_dict("records"):
            with self.subTest(trend_id=row["trend_id"]):
                for field in ("evidence_summary", "source_name", "source_url", "interpretation_limitations"):
                    self.assertTrue(row[field].strip(), field)
                self.assertEqual(urlparse(row["source_url"]).scheme, "https")
                self.assertTrue(urlparse(row["source_url"]).netloc)
                self.assertIn(row["trend_direction"], TREND_DIRECTIONS)
                self.assertIn(row["evidence_type"], EVIDENCE_TYPES)
                self.assertIn(row["confidence_level"], CONFIDENCE_LEVELS)
                self.assertIn(row["verification_status"], VERIFICATION_STATUSES)
                retrieved = date.fromisoformat(row["retrieved_date"])
                self.assertLessEqual(retrieved, date.today())
                if row["publication_date"]:
                    self.assertLessEqual(date.fromisoformat(row["publication_date"]), retrieved)
                else:
                    self.assertEqual(row["verification_status"], "requires_verification")

    def test_missing_publication_days_and_mixed_forecasts_are_not_overstated(self) -> None:
        trends = get_trends().set_index("trend_id")
        for trend_id in ("MY-TREND-001", "MY-TREND-002"):
            with self.subTest(trend_id=trend_id):
                self.assertEqual(trends.loc[trend_id, "publication_date"], "")
                self.assertEqual(trends.loc[trend_id, "verification_status"], "requires_verification")
                self.assertEqual(trends.loc[trend_id, "evidence_type"], "report")
        for trend_id in ("MY-TREND-003", "MY-TREND-004", "MY-TREND-005"):
            with self.subTest(trend_id=trend_id):
                self.assertEqual(trends.loc[trend_id, "verification_status"], "verified")
                self.assertEqual(trends.loc[trend_id, "evidence_type"], "forecast")
        self.assertEqual(trends.loc["MY-TREND-005", "trend_direction"], "uncertain")

    def test_existing_accessors_filter_evidence_without_enabling_scenarios(self) -> None:
        self.assertEqual(
            set(get_trends("MY-CAND-001")["trend_id"]),
            {"MY-TREND-001", "MY-TREND-004"},
        )
        self.assertTrue(get_trends("MY-CAND-007").empty)
        trends = get_trends()
        self.assertTrue(trends["is_scenario_input"].eq("false").all())
        for column in ("scenario_relevance", "proposed_scenario_adjustment", "adjustment_basis"):
            self.assertTrue(trends[column].eq("").all())
        self.assertTrue(get_scenario_inputs().empty)


if __name__ == "__main__":
    unittest.main()
