"""Score how well a person's skills match a set of roles."""

import json
import re
from pathlib import Path


def _as_list(values):
    """Treat one string as one item, and safely handle an empty value."""
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return list(values)


def _clean_skill(skill):
    """Make a skill lowercase and use one space between words."""
    return " ".join(str(skill).strip().lower().split())


def load_aliases(data_dir=None):
    """Read skill aliases from a folder or from the project's data folder."""
    if data_dir is None:
        aliases_path = (
            Path(__file__).resolve().parent / "data" / "skill_aliases.json"
        )
    else:
        aliases_path = Path(data_dir) / "skill_aliases.json"

    if not aliases_path.is_file():
        return {}

    with aliases_path.open(encoding="utf-8") as aliases_file:
        raw_aliases = json.load(aliases_file)

    if not isinstance(raw_aliases, dict):
        raise ValueError("data/skill_aliases.json must contain a JSON object.")

    return {
        _clean_skill(alias): _clean_skill(standard)
        for alias, standard in raw_aliases.items()
        if _clean_skill(alias) and _clean_skill(standard)
    }


def canonical_skill(skill, aliases):
    """Convert a skill to its standard name and avoid alias loops."""
    cleaned = _clean_skill(skill)
    seen = set()

    while cleaned in aliases and cleaned not in seen:
        seen.add(cleaned)
        cleaned = aliases[cleaned]

    return cleaned


# Keep the earlier helper names available for existing callers.
_load_aliases = load_aliases
_canonical_skill = canonical_skill


def _contains_whole_skill(text, skill):
    """Check for a skill as a whole word or phrase, not as part of another word."""
    if not text or not skill:
        return False

    pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
    return re.search(pattern, text, flags=re.UNICODE) is not None


def _get_weight(skill, weights, aliases):
    """Use a configured skill weight, or 1 when no weight is provided."""
    if not weights:
        return 1

    normalized_weights = {
        canonical_skill(name, aliases): weight
        for name, weight in weights.items()
    }
    return normalized_weights.get(skill, 1)


def score_roles(
    skills,
    roles,
    weights=None,
    skills_to_ignore=None,
    role_weights=None,
):
    """Return each role's weighted skill match, sorted from best to worst."""
    aliases = load_aliases()

    # Normalize the user's skills and the skills they want excluded.
    user_skills = [
        canonical_skill(skill, aliases)
        for skill in _as_list(skills)
        if _clean_skill(skill)
    ]
    ignored_skills = [
        canonical_skill(skill, aliases)
        for skill in _as_list(skills_to_ignore)
        if _clean_skill(skill)
    ]
    user_skills = [
        skill
        for skill in user_skills
        if not any(
            _contains_whole_skill(skill, ignored_skill)
            for ignored_skill in ignored_skills
        )
    ]

    results = []

    # Score each role using only the skills that role requires.
    for role_name, required_skills in roles.items():
        required = []
        seen_required = set()
        for skill in _as_list(required_skills):
            if not _clean_skill(skill):
                continue

            normalized_skill = canonical_skill(skill, aliases)
            if normalized_skill not in seen_required:
                required.append(normalized_skill)
                seen_required.add(normalized_skill)

        # Combine role-specific base weights with optional scenario weights.
        base_weights = {}
        if role_weights is not None:
            role_skill_weights = role_weights.get(role_name, {})
            normalized_role_weights = {
                canonical_skill(name, aliases): weight
                for name, weight in role_skill_weights.items()
            }
            base_weights = {
                skill: normalized_role_weights.get(skill, 1)
                for skill in required
            }

        skill_weights = {
            skill: base_weights.get(skill, 1) * _get_weight(skill, weights, aliases)
            for skill in required
        }
        total_weight = sum(skill_weights.values())

        have = []
        missing = []
        breakdown = []
        matched_weight = 0

        # Give credit only when a required skill appears as a whole word.
        for skill in required:
            has_skill = any(
                _contains_whole_skill(user_skill, skill)
                for user_skill in user_skills
            )
            weight = skill_weights[skill]

            if has_skill:
                have.append(skill)
                matched_weight += weight
                contribution = (
                    round(weight / total_weight * 100, 2)
                    if total_weight
                    else 0
                )
                status = "have"
            else:
                missing.append(skill)
                contribution = 0
                status = "missing"

            breakdown.append(
                {
                    "skill": skill,
                    "status": status,
                    "weight": weight,
                    "contribution": contribution,
                }
            )

        # An empty skill list or zero total weight gives a score of zero.
        score = (
            min(
                100,
                max(0, int(matched_weight / total_weight * 100 + 0.5)),
            )
            if total_weight
            else 0
        )

        if score >= 70:
            tier = "Strong"
        elif score >= 40:
            tier = "Moderate"
        else:
            tier = "Stretch"

        results.append(
            {
                "role": role_name,
                "score": score,
                "tier": tier,
                "skills_have": have,
                "skills_missing": missing,
                "breakdown": breakdown,
            }
        )

    # Sorting is stable, so tied roles keep their original order.
    return sorted(results, key=lambda result: result["score"], reverse=True)
