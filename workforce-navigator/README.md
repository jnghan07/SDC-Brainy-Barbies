# Aiversecity Future-Ready Workforce Navigator — Data Component

A small, standalone Python/pandas component for role, labour-market evidence,
course, and SDG data. It does not depend on Streamlit or the TypeScript API
Server. The CSVs are a starter contract, not a verified labour-market dataset.

## Project layout

```text
workforce-navigator/
  data/                 # Four source-of-truth CSV files
  modules/trend_data.py # Validated, importable pandas API
  scripts/              # Manual data preflight commands
  tests/                # Contract and validation tests
  requirements.txt
```

## Setup and checks

Use Python 3.10+ and install the project dependency:

```bash
cd workforce-navigator
python -m pip install -r requirements.txt
python scripts/validate_data.py
python -m unittest discover -s tests -v
```

The validator exits non-zero when files or rows fail validation. No test data
or generated output is mixed into `data/`.

## Import contract

Change into this standalone project directory before importing:

```python
from modules.trend_data import (
    get_courses,
    get_role,
    get_role_skills,
    get_roles,
    get_scenario_inputs,
    get_sdg_mappings,
    get_trends,
    validate_datasets,
)
```

When calling the component from another project, add this directory to
`PYTHONPATH` or install/package it according to the consuming project's setup.
Each accessor accepts an optional keyword-only `data_dir` for fixture or
alternate-dataset testing.

### Return values and errors

| Function | Return |
| --- | --- |
| `get_roles()` | Copy of the roles pandas DataFrame |
| `get_role(role_id)` | Copy of one role as a pandas Series |
| `get_trends(role_id=None)` | Trends DataFrame, optionally filtered by a known role ID |
| `get_courses(skill=None)` | Verified courses DataFrame only; optional canonical skill/alias filter |
| `get_sdg_mappings(role_id=None)` | Candidate and verified mappings DataFrame |
| `get_role_skills(role_id)` | List of canonical skill strings |
| `get_scenario_inputs()` | Verified trend evidence marked for scenario consideration, as a DataFrame |
| `validate_datasets()` | Dictionary with `valid`, `errors`, `warnings`, and `record_counts` |
| `load_datasets()` | Dictionary mapping each dataset name to its DataFrame |

Unknown role IDs raise `KeyError`. Unknown skill labels raise `ValueError`.
Invalid files or rows cause `load_datasets()` and the retrieval functions to
raise `DatasetValidationError` with all validation messages; rows are never
silently dropped. `validate_datasets()` itself returns errors rather than
raising, making it suitable for a preflight check. Empty trend/course files
are valid and produce an informational warning.

Example:

```python
roles = get_roles()
skills = get_role_skills("MY-CAND-001")
quality = validate_datasets()
```

## Schemas

All four CSVs have a header row. Blank source fields are allowed for candidate
records; when a record is `verified`, source evidence and required dates/URLs
are validated.

### `roles.csv`

`role_id` (stable join key), `role_name`, `role_description`,
`required_skills` (JSON array of canonical labels), `skill_weights` (JSON
object mapping each required skill label to an integer weight from 1 to 3), `occupation_source`,
`source_url`, `verification_status`, and `record_notes`.

The 10 `MY-CAND-*` rows are proposed role examples for Malaysian students and
fresh graduates. Some descriptions and skill labels now reflect relevant
Malaysian occupational frameworks, but every row remains `candidate_unverified`:
framework examples do not establish universal employer requirements or confirm
fresh-graduate suitability. `skill_weights` values are explicit project
assumptions about relative priority, not official occupational ratings or
verified evidence. They do not change a role's verification status and should
not be presented as authoritative or as an approved scoring model.

### `trends.csv`

`trend_id`, `role_id`, `skill_name`, `trend_direction` (`increasing`, `stable`,
`decreasing`, or `uncertain`), `evidence_summary`, `source_name`, `source_url`,
`publication_date`, `retrieved_date`, `evidence_type`, `confidence_level`,
`verification_status`, `is_scenario_input`, `scenario_relevance`,
`proposed_scenario_adjustment`, `adjustment_basis`, and
`interpretation_limitations`.

The starter file contains only a header. No labour-market trends, statistics,
dates, sources, confidence assessments, or scenario adjustments have been
invented. A scenario input must be marked verified and remain evidence plus a
documented proposal; this component never calculates scenario outcomes.

### Malaysian trend-source review (2026-10-23)

The trend file remains header-only because the sources reviewed did not meet
the combined requirement for clear reuse permission, a dated change in Malaysian
skill demand, and a direct match to a canonical skill used by an existing role.
No claims below have been entered as trends:

- **Tee et al., “Demand for digital skills, skill gaps and graduate
  employability”** (first published 2024-04-25,
  [article](https://f1000research.com/articles/13-389),
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)). The Malaysian
  employer survey compares current ratings with employers’ expected future
  ratings, including increases for “communication and collaboration,”
  “problem-solving,” and “safety.” This is a forecast comparison, not an
  observed labour-demand time series. “Communication and collaboration” is a
  combined measure, not the component’s standalone `Communication` skill;
  “problem-solving” and “safety” also do not directly match canonical skills.
  These results are therefore not assigned to narrower skill labels.
- **Hays Malaysia, “AI drives decline in Software Development roles”**
  (published 2025-03-07,
  [release](https://www.hays.com.my/press-release/content/future-of-work-malaysia-technology-ai-impact)).
  The release reports a 32% reduction in Malaysian Software Development demand
  between 2022 and 2024, an exact skill-label and period match. However,
  [Hays Malaysia’s terms](https://www.hays.com.my/terms-and-conditions) state
  that site information is its copyright and prohibit copying or distribution
  for business or commercial use. No separate data reuse permission was found,
  so this claim is not reproduced in the CSV.
- **OpenDOSM, Quarterly Skills-Related Underemployment by Age**
  ([dataset](https://open.dosm.gov.my/data-catalogue/lfs_qtr_sru_age),
  data available from 2017 and updated 2026-08-11,
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)). The reusable
  series measures tertiary-educated workers in semi-skilled or low-skilled
  occupations classified under MASCO; it does not measure demand for the
  component’s individual canonical skills.
- **LinkedIn Future of Skills**
  ([explorer](https://linkedin.github.io/future-of-skills)) includes Malaysia
  and compares worker skill profiles across years, but its page says LinkedIn
  data is governed by the LinkedIn User Agreement. It describes changes in
  member skill profiles, not Malaysian employer demand, and does not provide
  clear independent reuse terms for this dataset.

The exclusions are intentional: no demand direction is inferred by mapping a
broad occupation group, a composite skill, or worker profile prevalence onto a
narrower canonical skill. Revisit these sources only if suitable reuse
permission and directly aligned skill-level demand evidence become available.

### `courses.csv`

`course_id`, `course_name`, `provider`, `target_skills` (JSON array),
`course_url`, `cost_status`, `availability_status`, `last_verified_date`,
`source_url`, `verification_status`, and `record_notes`.

The starter file has no candidate course details because no provider course
page has been checked. `get_courses()` returns verified entries only; course
names, providers, prices, availability, and URLs must never be guessed.

### `sdg_mappings.csv`

`role_id`, `sdg_id` (1–17), `sdg_name`, `mapping_rationale`,
`supporting_evidence`, `source_url`, `verification_status`, and `record_notes`.

The two Sustainability Analyst examples are hypotheses, labelled
`candidate_unverified`. Their source URLs point to the official UN Goal 12 and
Goal 13 pages, but supporting role-specific evidence remains blank. The UN
targets establish the goal wording, not a link to this occupation. Do not treat
either mapping as verified without evidence tied to actual role duties.

## Skill vocabulary

`required_skills`, trend `skill_name`, and course `target_skills` use exact
canonical labels from `CANONICAL_SKILLS` in `modules/trend_data.py`. Matching
is case-insensitive and trims extra spaces. Supported aliases normalize to:

- `ML`, `AI/ML`, `Machine Learning (ML)` → `Machine Learning`
- `UI`, `UX`, `UX/UI` → `UI/UX Design`
- `data visualisation` → `Data Visualization`
- `human resource management` → `Human Resources`
- `search engine optimisation` / `search engine optimization` → `SEO`

Add and document new canonical labels and aliases in the module before using
them in a CSV. Unknown labels are validation errors rather than silently
rewritten values.

## Evidence review and update workflow

1. Prefer Malaysian public sources relevant to the claim (for example, official
   labour statistics, occupational publications, or provider course pages).
2. Before collecting anything, check whether a public API or downloadable
   report exists and read its access and reuse terms. A public webpage does
   not imply an API or permission to scrape.
3. If terms or access are unclear, use a manual review process and record only
   the information that can be checked. This project includes no crawler,
   scraper, scheduler, or assumed organization API.
4. Enter candidate records with `candidate_unverified` or
   `requires_verification`. Keep source names/URLs/dates blank when they have
   not actually been checked. Do not mark a claim verified until the source,
   evidence, and dates are traceable.
5. Normalize role IDs and skill labels, prepare an import CSV with the exact
   destination schema, and preview it before applying:

   ```bash
   python scripts/update_data.py --dataset roles --input reviewed_roles.csv
   python scripts/update_data.py --dataset roles --input reviewed_roles.csv --apply
   python scripts/validate_data.py
   ```

   The importer is dry-run by default. It reports `added`, `changed`,
   `unchanged`, `rejected`, and `needs_review`; valid candidate rows may be
   written with their unverified status intact, and are counted for review.
   Verified records cannot be replaced by unverified input. Changing a
   verified record requires a verified incoming row and the explicit
   `--confirm-verified-updates` option. The import file is checked against the
   full four-dataset schema and cross-references before each row is accepted.
   If some rows are rejected, valid rows can still be applied; the report names
   every rejected row and the command exits non-zero.

   Review changes manually; structural validation cannot establish whether a
   source is authoritative or an interpretation is correct.
6. For SDG mappings, check the official UN goal and relevant target, document
   how the specific role may contribute, and retain supporting evidence.
   Technology use alone is not a sufficient rationale.

There are no verified trend or course records as of this starter snapshot. No
trend or course data refresh date is claimed because neither dataset contains
records; the trend-source review above is dated separately.
This prototype must not be described as real-time or automatically updated.
The importer accepts manually reviewed CSVs, including records transcribed
from downloaded reports or exported from APIs whose access and reuse terms
have been checked. It does not fetch API data or scrape websites by itself.

## Validation coverage and limitations

Validation checks file presence/readability, required columns, duplicate IDs
and mapping pairs, blank keys, controlled status/value fields, JSON skill
formats, ISO dates, URL formats, and role references. It does not certify the
quality or reuse rights of source material. Tests use small fictional fixtures
to verify the interface and failure cases; those fixtures are not part of the
CSV datasets.
