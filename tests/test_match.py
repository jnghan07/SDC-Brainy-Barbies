"""Check career-match scores against the supplied profile examples."""

import json
import tempfile
import unittest
from pathlib import Path

from match import (
    _canonical_skill,
    _load_aliases,
    canonical_skill,
    load_aliases,
    score_roles,
)


FIXTURE_PATH = Path(__file__).with_name("test_profiles.json")


def load_profiles():
    """Load the role requirements and expected scores from the fixture."""
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class ScoreRolesTests(unittest.TestCase):
    """Verify that every fixture profile gets its expected score and tier."""

    def check_expected_scores(self, profile, expected, roles, skills_to_ignore=None):
        """Compare the actual score and tier for each expected role."""
        actual_results = score_roles(
            profile.get("skills", []),
            roles,
            skills_to_ignore=skills_to_ignore,
        )
        actual_by_role = {result["role"]: result for result in actual_results}

        for role_name, expected_result in expected.items():
            with self.subTest(profile=profile["id"], role=role_name):
                self.assertIn(role_name, actual_by_role)
                self.assertEqual(
                    actual_by_role[role_name]["score"],
                    expected_result["score"],
                )
                self.assertEqual(
                    actual_by_role[role_name]["tier"],
                    expected_result["tier"],
                )

    def test_every_profile_matches_expected_scores_and_tiers(self):
        """Check regular profiles and both versions of the claimed-skill profile."""
        fixture = load_profiles()
        roles = fixture["roles"]

        for profile in fixture["profiles"]:
            if (
                "expected_all_claimed" in profile
                and "expected_evidenced_only" in profile
            ):
                self.check_expected_scores(
                    profile,
                    profile["expected_all_claimed"],
                    roles,
                )
                self.check_expected_scores(
                    profile,
                    profile["expected_evidenced_only"],
                    roles,
                    skills_to_ignore=profile.get("claimed_only", []),
                )
            else:
                self.check_expected_scores(
                    profile,
                    profile["expected"],
                    roles,
                )

    def test_alias_file_maps_github_to_git(self):
        """An alternate spelling loaded from the alias file matches its standard skill."""
        result = score_roles(["github"], {"Example role": ["git"]})[0]
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["skills_have"], ["git"])

    def test_duplicate_normalized_required_skills_do_not_raise_score(self):
        """Duplicate skills, including aliases, count only once."""
        result = score_roles(
            ["git"],
            {"Example role": ["git", "github", "GIT"]},
        )[0]
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["skills_have"], ["git"])
        self.assertEqual(len(result["breakdown"]), 1)

    def test_ignoring_python_removes_python_with_extra_detail(self):
        """Ignoring a whole skill name also removes its more detailed form."""
        result = score_roles(
            ["Python (basic)"],
            {"Example role": ["python"]},
            skills_to_ignore=["python"],
        )[0]
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["skills_have"], [])

    def test_git_matches_inside_git_and_github_phrase(self):
        """A required skill matches as a whole word in a longer skill phrase."""
        result = score_roles(
            ["Git and GitHub"],
            {"Example role": ["git"]},
        )[0]
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["skills_have"], ["git"])

    def test_role_base_weights_score_three_to_one_as_75_percent(self):
        """Role-specific weights determine each required skill's contribution."""
        result = score_roles(
            ["a"],
            {"Example role": ["a", "b"]},
            role_weights={"Example role": {"a": 3, "b": 1}},
        )[0]
        self.assertEqual(result["score"], 75)
        self.assertEqual(
            [item["weight"] for item in result["breakdown"]],
            [3, 1],
        )

    def test_scenario_weights_multiply_role_base_weights(self):
        """Scenario weights multiply the base weights and are normalized by skill."""
        roles = {"Example role": ["a", "b"]}
        role_weights = {"Example role": {"a": 3, "b": 1}}
        weighted = score_roles(
            ["a"],
            roles,
            weights={"a": 2.0},
            role_weights=role_weights,
        )[0]
        only_b = score_roles(
            ["b"],
            roles,
            weights={"a": 2.0},
            role_weights=role_weights,
        )[0]
        self.assertEqual(weighted["score"], 86)
        self.assertEqual(
            [item["weight"] for item in weighted["breakdown"]],
            [6.0, 1],
        )
        self.assertEqual(only_b["score"], 14)

    def test_role_weights_none_keeps_existing_results(self):
        """Passing None for role weights is identical to the original scoring."""
        roles = {"Example role": ["a", "b"]}
        expected = score_roles(["a"], roles, weights={"a": 2.0})
        actual = score_roles(
            ["a"],
            roles,
            weights={"a": 2.0},
            role_weights=None,
        )
        self.assertEqual(actual, expected)

    def test_empty_skills_score_zero_with_role_weights(self):
        """No user skills gives a zero score even when base weights are set."""
        result = score_roles(
            [],
            {"Example role": ["a", "b"]},
            role_weights={"Example role": {"a": 3, "b": 1}},
        )[0]
        self.assertEqual(result["score"], 0)

    def test_alias_loader_uses_a_temporary_data_folder(self):
        """The loader reads a caller-provided alias file instead of default aliases."""
        with tempfile.TemporaryDirectory() as temporary_data_dir:
            aliases_path = Path(temporary_data_dir) / "skill_aliases.json"
            aliases_path.write_text(
                json.dumps({"ruby": "python"}),
                encoding="utf-8",
            )

            aliases = load_aliases(temporary_data_dir)

            self.assertEqual(aliases, {"ruby": "python"})
            self.assertEqual(canonical_skill("Ruby", aliases), "python")
            self.assertEqual(_canonical_skill("Ruby", aliases), "python")

        # The old loader name remains callable and still reads the default file.
        self.assertEqual(_load_aliases()["github"], "git")


if __name__ == "__main__":
    unittest.main()
