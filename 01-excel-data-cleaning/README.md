# Excel data cleaning: Chicago food inspections

A real, messy public dataset taken from raw export to an analysis-ready Excel workbook, with every change counted and logged.

**Deliverable:** [`deliverable/Chicago_Food_Inspections_Cleaned.xlsx`](deliverable/Chicago_Food_Inspections_Cleaned.xlsx)

| Sheet | Contents |
|---|---|
| Quality_Report | 11 before/after checks, each a live Excel formula on the Raw and Clean sheets |
| Summary | Fail rate by facility category, results by risk level, ten most-cited violations (formulas + charts) |
| Change_Log | 15 cleaning rules, rows touched, example before/after, and the Excel formula that does the same by hand |
| Clean | 5,941 inspections, one row each, with `data_flags` marking anything I filled or could not fix |
| Violations | 19,387 rows, one per violation, joined to Clean by `inspection_id` |
| Raw | The untouched download (6,000 rows) |
| Removed_Duplicates | The 59 rows dropped and which inspection each repeats |

## Source

City of Chicago Data Portal, [Food Inspections](https://data.cityofchicago.org/Health-Human-Services/Food-Inspections/4ijn-s7e5) (dataset `4ijn-s7e5`), Chicago Department of Public Health. First 6,000 records by `inspection_id`, covering 4 Jan 2010 to 9 May 2011, pulled from the portal's public API. Business names and addresses are public records of food establishments. No personal data.

## What was wrong, and what changed

| Problem in the raw data | Before | After |
|---|---|---|
| Addresses with leading, trailing or double spaces | 5,609 | 0 |
| City not exactly `CHICAGO` (`CCHICAGO`, `CHCHICAGO`, `chicago`, blank) | 43 | 0 (9 blanks filled and flagged) |
| Inspection date stored as text with a time part | 6,000 | 0 (real Excel dates) |
| License number `0` used as a placeholder | 26 | 0 (blank, flagged) |
| Facility type: free-text spellings | 85 | 13 categories (raw text kept) |
| Inspection type: spellings | 44 | 14 standard types (raw text kept) |
| Several violations packed into one text cell | 4,255 cells | 19,387 rows, one per violation |
| Messy `location` column duplicating latitude and longitude | 5,977 | dropped |
| Repeated inspection records | 59 | 0 (listed, reversible) |

## Findings from the cleaned data

Fail rate = Fail / (Pass + Pass with Conditions + Fail), categories with at least 40 inspections.

- Bars and liquor venues fail most often (52.9%, n=70), then wholesale and meat/fish (42.3%, n=71) and grocery and convenience stores (32.5%, n=730). Schools fail least (12.6%, n=507).
- Risk 1 (High) facilities fail 22.0% of the time and Risk 3 (Low) facilities fail 40.0% of the time (916 of 4,157 and 245 of 613 inspections). Counter-intuitive, and probably a selection effect: low-risk places are inspected mostly after complaints or license problems. I did not test that.
- The most-cited violations are about floors (34), walls and ceilings (35), equipment cleanliness (33) and ventilation (38).

These describe the first 17 months of the portal data only, not Chicago in general.

## Decisions you may want to reverse

1. **Duplicates.** Rows identical on license, address, date, type, result and violations count as one inspection. They could be genuine repeat visits entered twice on the same day. `Removed_Duplicates` lists every dropped row.
2. **Blank city** was filled with `CHICAGO` because every record comes from the Chicago health department. It is flagged.
3. **Category grouping** uses keyword rules in `src/clean.py`. 24 rows (kiosks, shelters, hotels) fall in `Other`; 246 blank facility types are `Unknown`.
4. **Missing risk level (7) and coordinates (23)** are left blank, not guessed.

## How it was built

The cleaning rules are scripted in Python (pandas) so a rerun gives identical results and every count is logged. The workbook is generated from the script's output, and its checks are live Excel formulas that I recalculated in Excel and compared with the cached values. The same rules can be done by hand with the formulas in `Change_Log` or with Power Query. If you send me a file like this, you get the same package: clean data, a log of every change, and a before/after report.

```bash
pip install -r ../requirements.txt
python src/clean.py            # writes data/clean/*.csv
python src/build_workbook.py   # writes deliverable/*.xlsx
pytest tests                   # 11 checks on the cleaned data
```

## Files

```
data/raw/        untouched download
data/clean/      inspections_clean.csv, violations_long.csv, removed_duplicates.csv, change_log.csv
deliverable/     the Excel workbook
src/             clean.py, build_workbook.py
tests/           test_clean.py
```
