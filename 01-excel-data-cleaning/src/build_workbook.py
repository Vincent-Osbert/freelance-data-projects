"""Build the Excel deliverable from the raw and cleaned CSVs.

Usage (from the project folder, after src/clean.py):
    python src/build_workbook.py

Formulas in Quality_Report and Summary are live Excel formulas. The values Python
computes are stored next to them as cached results, so the file also reads
correctly in viewers that do not recalculate.
"""
import re
from pathlib import Path

import pandas as pd
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "chicago_food_inspections_raw.csv"
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "deliverable" / "Chicago_Food_Inspections_Cleaned.xlsx"

raw = pd.read_csv(RAW, dtype=str, keep_default_na=False)
clean = pd.read_csv(CLEAN / "inspections_clean.csv", keep_default_na=False, na_values=[""], dtype={"zip": "string"})
viol = pd.read_csv(CLEAN / "violations_long.csv")
log = pd.read_csv(CLEAN / "change_log.csv", keep_default_na=False)
removed = pd.read_csv(CLEAN / "removed_duplicates.csv")

NR, NC, NV = len(raw), len(clean), len(viol)
RAW_LAST, CLEAN_LAST, VIOL_LAST = NR + 1, NC + 1, NV + 1

wb = xlsxwriter.Workbook(OUT, {"nan_inf_to_errors": False})
F = lambda **k: wb.add_format({"font_name": "Calibri", "font_size": 11, **k})
title = F(bold=True, font_size=16)
h = F(bold=True, bg_color="#1F3864", font_color="#FFFFFF", border=1, text_wrap=True, valign="vcenter")
cell = F(border=1, valign="top", text_wrap=True)
num = F(border=1, num_format="#,##0")
pct = F(border=1, num_format="0.0%")
datef = F(num_format="yyyy-mm-dd")
note = F(italic=True, font_color="#555555", text_wrap=True, valign="top")
good = F(border=1, num_format="#,##0", bg_color="#E2EFDA")
bad = F(border=1, num_format="#,##0", bg_color="#FCE4D6")
wrap = F(text_wrap=True, valign="top")

ws_readme = wb.add_worksheet("README")
ws_q = wb.add_worksheet("Quality_Report")
ws_s = wb.add_worksheet("Summary")
ws_log = wb.add_worksheet("Change_Log")
ws_c = wb.add_worksheet("Clean")
ws_v = wb.add_worksheet("Violations")
ws_raw = wb.add_worksheet("Raw")
ws_rm = wb.add_worksheet("Removed_Duplicates")
ws_raw.set_tab_color("#7F7F7F")
ws_rm.set_tab_color("#7F7F7F")
ws_c.set_tab_color("#548235")
ws_v.set_tab_color("#548235")

# ---------------------------------------------------------------- Raw (untouched)
for j, col in enumerate(raw.columns):
    ws_raw.write(0, j, col, h)
for i, row in enumerate(raw.itertuples(index=False), start=1):
    for j, v in enumerate(row):
        if v != "":
            ws_raw.write_string(i, j, v)
ws_raw.freeze_panes(1, 0)
ws_raw.set_column(0, 16, 16)

# ---------------------------------------------------------------- Clean
cols = list(clean.columns)
widths = {"inspection_id": 12, "inspection_date": 13, "facility_name": 34, "aka_name": 30, "license_no": 11,
          "facility_type_raw": 24, "facility_category": 22, "risk_level": 9, "risk_label": 10, "address": 28,
          "city": 10, "state": 6, "zip": 8, "latitude": 11, "longitude": 11, "inspection_type": 22,
          "inspection_type_raw": 24, "result": 20, "violation_count": 10, "data_flags": 30}
ws_c.add_table(0, 0, NC, len(cols) - 1, {"name": "CleanInspections", "style": "Table Style Light 1",
                                          "columns": [{"header": c} for c in cols]})
for i, r in enumerate(clean.itertuples(index=False), start=1):
    for j, v in enumerate(r):
        if pd.isna(v):
            continue
        c = cols[j]
        if c == "inspection_date":
            ws_c.write_datetime(i, j, pd.Timestamp(v).to_pydatetime(), datef)
        elif c in ("zip", "state", "city"):
            ws_c.write_string(i, j, str(v))
        elif isinstance(v, str):
            ws_c.write_string(i, j, v)
        else:
            ws_c.write_number(i, j, float(v))
for j, c in enumerate(cols):
    ws_c.set_column(j, j, widths.get(c, 14))
ws_c.freeze_panes(1, 3)

# ---------------------------------------------------------------- Violations
vcols = list(viol.columns)
ws_v.add_table(0, 0, NV, len(vcols) - 1, {"name": "ViolationsLong", "style": "Table Style Light 1",
                                          "columns": [{"header": c} for c in vcols]})
for i, r in enumerate(viol.itertuples(index=False), start=1):
    ws_v.write_number(i, 0, r.inspection_id)
    ws_v.write_number(i, 1, r.violation_no)
    ws_v.write_string(i, 2, r.violation_title)
    if isinstance(r.inspector_comment, str):
        ws_v.write_string(i, 3, r.inspector_comment)
ws_v.set_column(0, 1, 13)
ws_v.set_column(2, 2, 60)
ws_v.set_column(3, 3, 80)
ws_v.freeze_panes(1, 0)

# ---------------------------------------------------------------- Removed duplicates
for j, c in enumerate(removed.columns):
    ws_rm.write(0, j, c, h)
for i, r in enumerate(removed.itertuples(index=False), start=1):
    for j, v in enumerate(r):
        if not pd.isna(v):
            ws_rm.write(i, j, v if not isinstance(v, (int, float)) else float(v))
ws_rm.set_column(0, 6, 22)

# ---------------------------------------------------------------- Change log
for j, c in enumerate(["#", "Rule applied", "Column", "Rows touched", "Example before", "Example after", "Excel equivalent"]):
    ws_log.write(0, j, c, h)
for i, r in enumerate(log.itertuples(index=False), start=1):
    ws_log.write_number(i, 0, i, cell)
    ws_log.write_string(i, 1, r.rule, cell)
    ws_log.write_string(i, 2, r.column, cell)
    ws_log.write_number(i, 3, r.rows_changed, num)
    ws_log.write_string(i, 4, str(r.example_before), cell)
    ws_log.write_string(i, 5, str(r.example_after), cell)
    ws_log.write_string(i, 6, str(r.excel_equivalent), cell)
ws_log.set_column(0, 0, 4)
ws_log.set_column(1, 1, 60)
ws_log.set_column(2, 2, 16)
ws_log.set_column(3, 3, 12)
ws_log.set_column(4, 5, 32)
ws_log.set_column(6, 6, 52)
ws_log.freeze_panes(1, 0)

# ---------------------------------------------------------------- Quality report (live formulas)
def space_issue(s):
    return len(s) != len(re.sub(" +", " ", s.strip(" ")))

R = lambda col: f"Raw!{col}2:{col}{RAW_LAST}"
C = lambda col: f"Clean!{col}2:{col}{CLEAN_LAST}"
raw_addr_ws = int(sum(space_issue(v) for v in raw["address"]))
raw_name_ws = int(sum(space_issue(v) for v in raw["dba_name"]))
raw_city_bad = int(sum(v != "CHICAGO" for v in raw["city"]))
raw_license0 = int((raw["license_"] == "0").sum())
raw_loc = int((raw["location"] != "").sum())

ws_q.write(0, 0, "Data quality report: before and after", title)
ws_q.write(1, 0, "Every number in the Before and After columns is a live Excel formula on the Raw and Clean sheets.", note)
for j, c in enumerate(["Check", "Before (Raw)", "After (Clean)", "Status"]):
    ws_q.write(3, j, c, h)

rows = [
    ("Rows", f"=COUNTA({R('A')})", NR, f"=COUNTA({C('A')})", NC,
     f"{len(removed)} repeated inspection records removed (see Removed_Duplicates)"),
    ("Addresses with leading, trailing or double spaces",
     f"=SUMPRODUCT(--(LEN({R('G')})<>LEN(TRIM({R('G')}))))", raw_addr_ws,
     f"=SUMPRODUCT(--(LEN({C('J')})<>LEN(TRIM({C('J')}))))", 0, "Fixed"),
    ("Facility names with double spaces",
     f"=SUMPRODUCT(--(LEN({R('B')})<>LEN(TRIM({R('B')}))))", raw_name_ws,
     f"=SUMPRODUCT(--(LEN({C('C')})<>LEN(TRIM({C('C')}))))", 0, "Fixed"),
    ("City not exactly CHICAGO (typos, casing, blank)",
     f"=SUMPRODUCT(--NOT(EXACT({R('H')},\"CHICAGO\")))", raw_city_bad,
     f"=SUMPRODUCT(--NOT(EXACT({C('K')},\"CHICAGO\")))", 0, "Fixed; 9 blanks filled and flagged"),
    ("Inspection dates stored as text",
     f"=SUMPRODUCT(--ISTEXT({R('K')}))", NR,
     f"=SUMPRODUCT(--ISTEXT({C('B')}))", 0, "Fixed: real Excel dates"),
    ("License number is the placeholder 0",
     f"=COUNTIF({R('D')},0)", raw_license0, f"=COUNTIF({C('E')},0)", 0, "Set to blank and flagged"),
    ("Blank facility type",
     f"=COUNTBLANK({R('E')})", int((raw["facility_type"] == "").sum()),
     f"=COUNTBLANK({C('G')})", 0, "Labelled Unknown and flagged"),
    ("Cells holding several violations in one text",
     f"=COUNTA({R('N')})", int((raw["violations"] != "").sum()),
     f"=COUNTA(Violations!A2:A{VIOL_LAST})", NV, "After = one row per violation (Violations sheet)"),
    ("Rows with the messy 'location' column filled",
     f"=COUNTA({R('Q')})", raw_loc, "=0", 0, "Column dropped; latitude and longitude kept"),
    ("Rows missing risk level", f"=COUNTBLANK({R('F')})", int((raw["risk"] == "").sum()),
     f"=COUNTBLANK({C('H')})", int(clean["risk_level"].isna().sum()), "Left blank on purpose, flagged in data_flags"),
    ("Rows missing coordinates", f"=COUNTBLANK({R('O')})", int((raw["latitude"] == "").sum()),
     f"=COUNTBLANK({C('N')})", int(clean["latitude"].isna().sum()), "Left blank on purpose, flagged in data_flags"),
]
for i, (name, f1, v1, f2, v2, status) in enumerate(rows, start=4):
    ws_q.write(i, 0, name, cell)
    ws_q.write_formula(i, 1, f1, bad if v1 else num, v1)
    ws_q.write_formula(i, 2, f2, good if v2 == 0 else num, v2)
    ws_q.write(i, 3, status, cell)
r0 = 4 + len(rows) + 1
ws_q.write(r0, 0, "Checked in Python rather than by formula", F(bold=True))
static = [
    ("Distinct facility-type spellings", raw["facility_type"].replace("", pd.NA).dropna().str.lower().nunique(),
     clean["facility_category"].nunique(), "Grouped into categories; raw text kept in facility_type_raw"),
    ("Distinct inspection-type spellings", raw["inspection_type"].nunique(), clean["inspection_type"].nunique(),
     "Grouped; raw text kept in inspection_type_raw"),
]
for i, (name, b, a, status) in enumerate(static, start=r0 + 1):
    ws_q.write(i, 0, name, cell)
    ws_q.write_number(i, 1, b, bad)
    ws_q.write_number(i, 2, a, good)
    ws_q.write(i, 3, status, cell)
ws_q.set_column(0, 0, 52)
ws_q.set_column(1, 2, 16)
ws_q.set_column(3, 3, 60)

# ---------------------------------------------------------------- Summary (live formulas + charts)
ws_s.write(0, 0, "What the cleaned data shows", title)
ws_s.set_row(1, 32)
ws_s.write(1, 0, "Fail rate = Fail / (Pass + Pass with Conditions + Fail). 'Out of Business' visits are excluded. "
                 "Data covers 4 Jan 2010 to 9 May 2011 (first 6,000 records by inspection_id).", note)
ws_s.write(3, 0, "Fail rate by facility category", F(bold=True, font_size=12))
for j, c in enumerate(["Category", "Inspections with outcome", "Fails", "Fail rate"]):
    ws_s.write(4, j, c, h)
cats = [c for c in clean["facility_category"].value_counts().index if c not in ("Unknown", "Other")]
cats = [c for c in cats if (clean["facility_category"] == c).sum() >= 40]
G, Rr = C("G"), C("R")
for i, c in enumerate(cats, start=5):
    sub = clean[clean["facility_category"] == c]
    out = int(sub["result"].isin(["Pass", "Pass with Conditions", "Fail"]).sum())
    fails = int((sub["result"] == "Fail").sum())
    ws_s.write(i, 0, c, cell)
    ws_s.write_formula(i, 1, f'=COUNTIFS({G},A{i+1},{Rr},"Pass")+COUNTIFS({G},A{i+1},{Rr},"Pass with Conditions")+COUNTIFS({G},A{i+1},{Rr},"Fail")', num, out)
    ws_s.write_formula(i, 2, f'=COUNTIFS({G},A{i+1},{Rr},"Fail")', num, fails)
    ws_s.write_formula(i, 3, f"=C{i+1}/B{i+1}", pct, fails / out)
end1 = 5 + len(cats)
ch = wb.add_chart({"type": "bar"})
ch.add_series({"name": "Fail rate", "categories": ["Summary", 5, 0, end1 - 1, 0], "values": ["Summary", 5, 3, end1 - 1, 3],
               "fill": {"color": "#1F3864"}, "data_labels": {"value": True, "num_format": "0%"}})
ch.set_title({"name": "Fail rate by facility category"})
ch.set_legend({"none": True})
ch.set_x_axis({"num_format": "0%", "min": 0})
ch.set_y_axis({"reverse": True})
ch.set_size({"width": 560, "height": 340})
ws_s.insert_chart(3, 5, ch)

r2 = end1 + 2
ws_s.write(r2, 0, "Inspection results by risk level", F(bold=True, font_size=12))
for j, c in enumerate(["Risk", "Pass", "Pass with Conditions", "Fail"]):
    ws_s.write(r2 + 1, j, c, h)
for k, lab in enumerate(["High", "Medium", "Low"]):
    i = r2 + 2 + k
    ws_s.write(i, 0, lab, cell)
    for j, res in enumerate(["Pass", "Pass with Conditions", "Fail"], start=1):
        v = int(((clean["risk_label"] == lab) & (clean["result"] == res)).sum())
        ws_s.write_formula(i, j, f'=COUNTIFS({C("I")},$A{i+1},{Rr},"{res}")', num, v)
ch2 = wb.add_chart({"type": "column", "subtype": "percent_stacked"})
for j, color in zip(range(1, 4), ["#548235", "#BF9000", "#C00000"]):
    ch2.add_series({"name": ["Summary", r2 + 1, j], "categories": ["Summary", r2 + 2, 0, r2 + 4, 0],
                    "values": ["Summary", r2 + 2, j, r2 + 4, j], "fill": {"color": color}})
ch2.set_title({"name": "Results mix by risk level"})
ch2.set_size({"width": 560, "height": 300})
ws_s.insert_chart(21, 5, ch2)

r3 = r2 + 7
ws_s.write(r3, 0, "Ten most frequent violations", F(bold=True, font_size=12))
for j, c in enumerate(["Violation", "Times cited"]):
    ws_s.write(r3 + 1, j, c, h)
top = viol.groupby("violation_no").agg(n=("inspection_id", "size"), t=("violation_title", lambda s: s.mode().iat[0])).sort_values("n", ascending=False).head(10)
for i, (no, row) in enumerate(top.iterrows(), start=r3 + 2):
    ws_s.write_string(i, 0, f"{int(no)}. {row['t']}", cell)
    ws_s.write_formula(i, 1, f"=COUNTIF(Violations!$B$2:$B${VIOL_LAST},{int(no)})", num, int(row["n"]))
ws_s.set_column(0, 0, 78)
ws_s.set_column(1, 3, 16)

# ---------------------------------------------------------------- README
lines = [
    ("Chicago Food Inspections: cleaned workbook", title),
    ("", None),
    ("What this is", F(bold=True)),
    ("A real, messy public dataset taken from raw to analysis-ready. The Raw sheet is the untouched download; "
     "Clean is the result; Change_Log lists every rule with the number of rows it touched and the Excel formula "
     "that does the same thing by hand.", wrap),
    ("", None),
    ("Source", F(bold=True)),
    ("City of Chicago Data Portal, 'Food Inspections' (dataset 4ijn-s7e5), published by the Chicago Department of Public "
     "Health. First 6,000 records by inspection_id (inspections from 4 Jan 2010 to 9 May 2011), downloaded via the "
     "portal's public API. Business names and addresses are public records of food establishments; no personal data.", wrap),
    ("", None),
    ("Sheets", F(bold=True)),
    ("Quality_Report: before/after checks, live formulas.  Summary: fail rate by facility category, results by risk, "
     f"top violations.  Change_Log: {len(log)} rules.  Clean: {NC:,} rows, one per inspection.  Violations: {NV:,} rows, "
     f"one per violation, joined to Clean by inspection_id.  Raw: original {NR:,} rows.  Removed_Duplicates: the "
     f"{len(removed)} rows dropped and which inspection each repeats.", wrap),
    ("", None),
    ("Decisions worth knowing", F(bold=True)),
    ("1) Duplicates: rows identical on license, address, date, type, result and violations are treated as one "
     "inspection. They may be genuine repeat visits recorded the same day; the removed rows are listed so you can reverse this.\n"
     "2) Blank city (9 rows) was filled with CHICAGO because every record comes from the Chicago health department. Flagged in data_flags.\n"
     "3) License number 0 is a placeholder, not a real license; set to blank and flagged.\n"
     "4) Facility and inspection types are grouped by keyword rules; raw text is kept next to the group. "
     f"{int((clean.facility_category == 'Other').sum())} rows fall in 'Other' (kiosks, shelters, hotels) and "
     f"{int((clean.facility_category == 'Unknown').sum())} are blank ('Unknown').\n"
     f"5) Rows missing risk level ({int(clean.risk_level.isna().sum())}) or coordinates ({int(clean.latitude.isna().sum())}) are left blank, not guessed.", wrap),
    ("", None),
    ("How it was built", F(bold=True)),
    ("Cleaning rules are scripted in Python (src/clean.py, pandas) so the run is repeatable and every count is logged; "
     "this workbook is generated from the outputs. The same rules can be done by hand with the formulas in Change_Log "
     "or with Power Query. Tests in tests/ check the cleaned data.", wrap),
]
for i, (t, fmt) in enumerate(lines):
    if fmt is None:
        continue
    ws_readme.write(i, 0, t, fmt)
ws_readme.set_column(0, 0, 130)
for i in (3, 6, 9, 15):
    ws_readme.set_row(i, 80)
ws_readme.set_row(12, 195)

wb.close()
print("wrote", OUT)
