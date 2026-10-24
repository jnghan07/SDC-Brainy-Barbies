# Workforce trend evidence review

Review/retrieval date: 2026-10-23. No commit or push was performed.

## Why the file was empty

The evidence-data merge added 10 course records and course tests, but its
change set did not include the trends CSV. The accompanying catalogue tests
explicitly retained an expected trend count of zero. Inspection of the trends
file's Git history and the workspace found no populated alternate trends CSV
and no later deletion of trend records. The observable defect was omitted trend
work with a test that accepted the omission, not evidence lost in the merge.
The change set alone does not establish the previous executor's reasoning.

## Exact contract and preserved scope

The source of truth is `workforce-navigator/data/trends.csv`, not a root-level
`data/trends.csv`. Its 17 columns remain in their original order:

1. trend_id
2. role_id
3. skill_name
4. trend_direction
5. evidence_summary
6. source_name
7. source_url
8. publication_date
9. retrieved_date
10. evidence_type
11. confidence_level
12. verification_status
13. is_scenario_input
14. scenario_relevance
15. proposed_scenario_adjustment
16. adjustment_basis
17. interpretation_limitations

No role IDs, role skills, skill weights, role verification statuses, courses,
SDG mappings, public Python interfaces, matching logic, or website code were
changed. No scenario adjustment was added. All five rows have
`is_scenario_input=false`; the three scenario proposal fields remain blank.

## Proposed data changes

The complete field values are in the CSV diff. These are five evidence records,
not five independent studies. No vacancy statistics or growth percentages were
invented. The linked roles remain candidate profiles.

| ID | Role ID | Canonical skill | Direction | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| MY-TREND-001 | MY-CAND-001 | Data Analysis | increasing | TalentCorp: named skill demand in Malaysian GBS | requires_verification |
| MY-TREND-002 | MY-CAND-010 | Machine Learning | increasing | TalentCorp: named skill demand in Malaysian GBS | requires_verification |
| MY-TREND-003 | MY-CAND-003 | Cybersecurity | increasing | WEF: global 2025–2030 employer forecast | verified |
| MY-TREND-004 | MY-CAND-001 | Analytical Thinking | increasing | WEF: global 2025–2030 employer forecast | verified |
| MY-TREND-005 | MY-CAND-004 | UI/UX Design | uncertain | WEF: contrasting industry forecasts for design/user experience | verified |

All confidence values are `medium`. The TalentCorp findings are qualitative
sector conclusions, not measured time series. WEF findings are surveyed
employers' expectations, not observed Malaysian hiring outcomes.

`Analytical Thinking` is already a canonical label. Its trend-to-role link is
contextual; it does not add a required skill to the Data Analyst profile.
The WEF design/user-experience category is mapped transparently to the existing
`UI/UX Design` label, without asserting separate demand for UI tools or user
research. Its uncertain direction preserves the conflicting sector evidence.

## Sources checked and decisions

Five primary report sources were reviewed: two used and three excluded.
The WEF report was reviewed in two chapters but counts as one report source.
The official TalentCorp launch release and HRD Corp reports index were also
checked as supporting publication pages. Two additional TalentCorp PDF
endpoints failed text extraction and were not used for claims.

### Used: TalentCorp GBS workforce impact study (2024)

[Direct report](https://www.talentcorp.com.my/images/uploads/publication/198/Impact-Study-of-Artificial-Intelligence-Digital-and-Green-Economy-on-the-Malaysian-Workforce-Volume-2-Sector-Global-Business-Services-1747879429.pdf)

Chapter 4, “Highly Impacted Roles and Career Pathways”, printed pp. 52–53
(PDF page 27) explicitly describes increasing demand for professionals skilled
in data analysis and machine learning. Only these explicitly named capabilities
were used, not the report's broad AI transformation findings or its occupation
counts. Both rows share this finding and are not independent corroboration.

The PDF shows copyright year 2024, not an exact publication day. The
[official launch release](https://www.talentcorp.com.my/resources/press-releases/talentcorp-launches-landmark-study-on-workforce-impact-of-ai-digitalisation-and-green-economy)
is dated 18 November 2024, but this does not establish the exact publication
day of this specific PDF volume/version. The CSV therefore leaves publication
date blank. Under the existing validator, verified trend records require a full
publication date; both rows remain `requires_verification`. Their factual
finding was checked, but they must not be represented as fully verified records.

### Used: WEF Future of Jobs Report 2025

Publication date: 7 January 2025.

- [Chapter 3: Skills outlook](https://www.weforum.org/publications/the-future-of-jobs-report-2025/in-full/3-skills-outlook/),
  section 3.2, “Skill evolution” and “Core skills in 2030”: explicitly rising
  importance for the networks/cybersecurity category and analytical thinking.
  These findings do not establish growth for Python, SQL, Machine Learning,
  Statistics, or any other narrower skill.
- [Chapter 5: Industry insights](https://www.weforum.org/publications/the-future-of-jobs-report-2025/in-full/5-region-economy-and-industry-insights/),
  section 5.2: advanced-manufacturing respondents expect growing demand for
  design/user-experience skills. IT-services respondents more frequently
  anticipate decline than respondents in other industries. That comparison
  does **not** establish a net decline for IT services or one overall trend.
  The CSV deliberately records `uncertain`.

All three WEF rows are `forecast` evidence. Verification means the stated
forecast was traced to the report, not that the forecast is guaranteed or that
the candidate role is verified.

### Excluded: HRDF/HRD Corp Data Analyst intelligence report

[Demand, Skills and Training for Data Analyst, No. 1/2020](https://hrdcorp.gov.my/wp-content/uploads/2021/03/1_2020_INDUSTRY-TRAINING-INTELLIGENCE-REPORT.pdf)

This directly discusses SQL and Python in job advertisements, among other
skills, but its job-portal data are as of February 2020. It cannot establish
current growth in demand. The March 2021 URL path is not proof of publication
date. It was not used to pad the catalogue with old snapshots.

### Excluded: HRD Corp National Training Index 2024

[Direct report](https://hrdcorp.gov.my/wp-content/uploads/2025/04/NTI.2024-upd18042025.pdf)

The front matter explicitly restricts reproduction or use without express
written permission except brief quotations in book reviews. No records were
derived from it. Training enrolment also must not be relabelled as employer
demand without a direct supporting finding.

### Excluded: MDEC Digital Talent Snapshot Q3 2024

[Direct report](https://www.mdec.my/api/media/file/Digital_Talent_Snapshot_Q3_2024_1_compressed.pdf)

The confidentiality/disclaimer requires prior written consent for circulation
or reproduction and reserves rights over unauthorised use of the information.
No record uses its skill lists or figures. A list of in-demand skills would
also not, by itself, establish increasing demand over time.

### Inaccessible extraction candidates

TalentCorp's Volume 1 overview and Volume 2 ICT report returned extraction
errors. Search excerpts were not used as verified evidence. The GBS report also
failed extraction initially, but its public PDF was subsequently downloaded
and its actual text checked.

## Access and reuse scope

This was a manual source review, not a crawler, API, or refresh pipeline.
The included summaries are original, short factual paraphrases with attribution.
No report tables, graphics, or substantive passages are redistributed.
TalentCorp's PDF carries an all-rights-reserved reproduction notice; WEF's
pages advertise CC BY-NC-ND republishing conditions. These citations and
original factual summaries do not grant permission to republish report
assets or copyrighted text. Recheck those conditions before such reuse.
Sources with express restrictions on use of the information were excluded.

## Unresolved evidence gaps

- Confirm an exact publication day for the TalentCorp GBS volume if those
  two records are to become `verified` under the unchanged validator.
- No Malaysian skill-demand growth rates or observed 2026 trends were
  established. Global WEF forecasts must not be presented as Malaysian data.
- No supported directional records were added for individual programming
  languages, SEO, finance, supply-chain/logistics, sustainability reporting,
  people analytics, or every other existing role/skill combination.
- Occupation shortages, static framework competencies, tool examples and
  broad AI trends are not substitutes for direct skill-demand evidence.
- Five records were preferred to filling a 10–20 record quota with weak claims.

## Verification

Run from `workforce-navigator/`:

```text
python scripts/validate_data.py
python -m unittest discover -s tests -v
```

Catalogue regression checks now reject a header-only trends file, verify its
exact 17-column structure and canonical references, preserve the two pending
publication dates, keep the mixed design/UX signal uncertain, and check the
existing filtering and scenario accessors without changing them.

Results on 2026-10-23:

- Validator: `valid=true`, zero errors and zero warnings.
- Record counts: 10 roles, 5 trends, 10 courses, 2 SDG mappings.
- Unit tests: all 23 passed, including five new trend-catalogue regression tests.
- Three trends have verified forecast metadata; two TalentCorp findings remain
  `requires_verification` for the unresolved exact publication date.
