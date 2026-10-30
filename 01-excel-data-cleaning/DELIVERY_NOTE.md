# Sample delivery note (what a client receives with the files)

**Files:** `Chicago_Food_Inspections_Cleaned.xlsx` (sheets Clean, Violations, Raw, Change_Log, Quality_Report, Summary, Removed_Duplicates) and the same data as CSV.

**What I changed:** 15 rules, each listed in Change_Log with rows touched. Main ones: 59 repeated records removed, 5,609 addresses trimmed, 34 city typos and 9 blank cities set to CHICAGO, text dates converted to real dates, facility types grouped into 13 categories (original text kept).

**What I found:** fail rate varies from 12.6% (schools) to 52.9% (bars and liquor).

**What I am unsure about:** the 59 removed rows could be genuine repeat visits (listed in Removed_Duplicates, easy to restore); 246 blank facility types are labelled Unknown, not guessed; 7 rows have no risk level and 23 no coordinates.

**Next step if useful:** merge with a second month of data, or add a pivot-based dashboard.
