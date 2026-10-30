"""Clean the raw Chicago Food Inspections extract.

Usage (from the project folder):
    python src/clean.py

Reads  data/raw/chicago_food_inspections_raw.csv
Writes data/clean/inspections_clean.csv
       data/clean/violations_long.csv
       data/clean/removed_duplicates.csv
       data/clean/change_log.csv
Every rule is logged with the number of rows it touched, so the result can be audited.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "chicago_food_inspections_raw.csv"
OUT = ROOT / "data" / "clean"

FACILITY_RULES = [  # first match wins; order matters
    ("Daycare & Children", r"daycare|day care|children|kids|preschool|pre-school|nursery|head start"),
    ("School", r"school|college|university|educational|culinary|teaching|cooking"),
    ("Long-term Care & Health", r"long term|nursing|hospital|assisted|care facility|clinic|pharmacy|drug store"),
    ("Mobile Food", r"mobile|food truck|dispenser|hot dog|cart"),
    ("Bakery", r"bakery|baker"),
    ("Coffee & Cafe", r"coffee|cafe|espresso|juice|ice cream|gelato|candy"),
    ("Bar & Liquor", r"tavern|bar$|^bar|liquor|brewery|lounge|pub"),
    ("Catering & Events", r"catering|banquet|event|church|hall|theater|stadium|concession"),
    ("Wholesale & Meat/Fish", r"wholesale|butcher|poultry|fish|slaughter|meat|distribut|warehouse|commissary|incubator"),
    ("Grocery & Convenience", r"grocery|convenience|mini mart|gas station|retail|food mart|supermarket|store|liquor store"),
    ("Restaurant", r"rest|diner|taqueria|pizza|sushi|buffet|food court|cafeteria|kitchen|grill|deli"),
]

INSPECTION_RULES = [
    ("Special Event", r"taste of chicago|rib fest|special events|festival"),
    ("Task Force", r"task force|package liquor|package goods"),
    ("Suspected Food Poisoning", r"poisoning"),
    ("Out of Business", r"out of business"),
    ("Tag Removal", r"tag removal"),
    ("Consultation", r"consultation|haccp"),
    ("Short Form Complaint", r"short form|sfp"),
    ("Complaint Re-inspection", r"complaint.*re-?inspection"),
    ("Complaint", r"complaint"),
    ("License Re-inspection", r"license.*re-?inspection"),
    ("License", r"license"),
    ("Canvass Re-inspection", r"canvass re-?inspection|re-?inspection|close-up"),
    ("Canvass", r"canvass"),
]

LOG: list[dict] = []


def log(rule, column, rows, before, after, excel):
    LOG.append(dict(rule=rule, column=column, rows_changed=int(rows), example_before=before,
                    example_after=after, excel_equivalent=excel))


def collapse(s: pd.Series) -> pd.Series:
    return s.str.replace(r"\s+", " ", regex=True).str.strip()


def categorize(value, rules, default="Other"):
    if pd.isna(value):
        return None
    v = str(value).lower()
    for label, pattern in rules:
        if re.search(pattern, v):
            return label
    return default


def clean(raw: pd.DataFrame):
    df = raw.copy()
    n0 = len(df)

    # ---- text columns: whitespace + case
    for col, new in [("dba_name", "facility_name"), ("aka_name", "aka_name"), ("address", "address")]:
        s = df[col]
        changed = (s.notna() & (s != collapse(s))).sum()
        up = s.where(s.isna(), collapse(s).str.upper())
        up_changed = (s.notna() & (s != up)).sum()
        log(f"Trim, collapse repeated spaces, UPPERCASE {col}", col, up_changed,
            s[s != up].dropna().iloc[0] if up_changed else "", up[s != up].dropna().iloc[0] if up_changed else "",
            f"=UPPER(TRIM({col}))")
        df[new] = up
    df = df.drop(columns=["dba_name"]) if "dba_name" in df and "facility_name" in df else df

    # ---- city
    city_raw = df["city"]
    city = city_raw.str.upper().str.strip()
    typo = city.notna() & ~city.eq("CHICAGO")
    city = city.where(~typo, "CHICAGO")
    log("Fix city typos and casing (CCHICAGO, CHCHICAGO, chicago, ...)", "city",
        (city_raw.notna() & (city_raw != city)).sum(), "CCHICAGO", "CHICAGO", '=IF(ISNUMBER(SEARCH("CHICAGO",UPPER(city))),"CHICAGO",city)')
    miss_city = city.isna()
    city = city.fillna("CHICAGO")
    log("Fill blank city with CHICAGO (all records come from the Chicago health department; flagged)", "city",
        miss_city.sum(), "(blank)", "CHICAGO", '=IF(city="","CHICAGO",city)')
    df["city"] = city

    # ---- license
    lic = pd.to_numeric(df["license_"], errors="coerce")
    zero = lic.eq(0)
    log("License 0 is a placeholder, set to blank (flagged)", "license_", zero.sum(), "0", "(blank)",
        '=IF(license=0,"",license)')
    df["license_no"] = lic.mask(zero).astype("Int64")

    # ---- facility type
    ft_raw = df["facility_type"].where(df["facility_type"].isna(), collapse(df["facility_type"]))
    cat = ft_raw.map(lambda v: categorize(v, FACILITY_RULES))
    log("Group free-text facility types into categories (raw text kept)", "facility_type",
        (ft_raw.notna()).sum(), "Coffee shop / coffee shop / COFFEE SHOP", "Coffee & Cafe",
        "keyword lookup: =IFERROR(VLOOKUP(\"*\"&keyword&\"*\",map,2,0),\"Other\") or Power Query conditional column")
    miss_ft = cat.isna()
    cat = cat.fillna("Unknown")
    log("Blank facility type labelled Unknown (flagged)", "facility_type", miss_ft.sum(), "(blank)", "Unknown", '=IF(type="","Unknown",type)')
    df["facility_type_raw"] = ft_raw
    df["facility_category"] = cat

    # ---- risk
    risk_n = df["risk"].str.extract(r"Risk (\d)")[0].astype("Int64")
    label = risk_n.map({1: "High", 2: "Medium", 3: "Low"})
    log("Split 'Risk 1 (High)' into numeric level and label", "risk", risk_n.notna().sum(),
        "Risk 1 (High)", "1 / High", '=VALUE(MID(risk,6,1))')
    df["risk_level"] = risk_n
    df["risk_label"] = label

    # ---- dates
    d = pd.to_datetime(df["inspection_date"], errors="coerce").dt.normalize()
    log("Convert text timestamp to a real date (time part was always 00:00)", "inspection_date", d.notna().sum(),
        "2010-01-05T00:00:00.000", "2010-01-05", "=DATEVALUE(LEFT(date,10))")
    df["inspection_date"] = d

    # ---- inspection type
    it_raw = collapse(df["inspection_type"])
    it = it_raw.map(lambda v: categorize(v, INSPECTION_RULES))
    it = it.fillna("Other")
    log("Group 44 inspection-type spellings into standard types (raw kept)", "inspection_type",
        (it_raw != it).sum(), "REINSPECTION / RE-INSPECTION OF CLOSE-UP", "Canvass Re-inspection",
        "keyword lookup or Power Query conditional column")
    df["inspection_type_raw"] = it_raw
    df["inspection_type"] = it

    # ---- results
    res = df["results"].str.strip().replace({"Pass w/ Conditions": "Pass with Conditions"})
    log("Spell out 'Pass w/ Conditions'", "results", (df["results"] != res).sum(), "Pass w/ Conditions",
        "Pass with Conditions", '=SUBSTITUTE(result,"w/","with")')
    df["result"] = res

    # ---- violations
    viol = df["violations"]
    df["violation_count"] = viol.map(lambda v: 0 if pd.isna(v) else len(re.split(r" \| (?=\d+\. )", v)))
    log("Count violations packed in one cell (split into Violations sheet)", "violations", (viol.notna()).sum(),
        "30. FOOD IN ORIGINAL ... | 33. ...", "violation_count = 2", '=LEN(v)-LEN(SUBSTITUTE(v," | ",""))/3+1')

    # ---- coordinates
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    no_geo = df["latitude"].isna() | df["longitude"].isna()
    log("Drop messy 'location' column (duplicate of latitude/longitude with stray newlines)", "location",
        df["location"].notna().sum(), "\\n,  \\n(41.9, -87.6)", "(removed)", "delete column")

    # ---- flags
    flags = pd.DataFrame({
        "city_filled": miss_city, "license_missing": zero, "facility_type_missing": miss_ft,
        "risk_missing": risk_n.isna(), "no_geo": no_geo})
    df["data_flags"] = flags.apply(lambda r: ";".join(k for k, v in r.items() if v), axis=1)

    # ---- duplicates
    key = ["license_no", "address", "inspection_date", "inspection_type", "result", "violations"]
    key_df = df[key].astype(str)
    dup = key_df.duplicated(keep="first")
    removed = df[dup][["inspection_id", "facility_name", "address", "inspection_date", "inspection_type", "result"]].copy()
    first_id = df.assign(_k=key_df.agg("|".join, axis=1)).groupby("_k")["inspection_id"].transform("first")
    removed["duplicate_of_inspection_id"] = first_id[dup]
    log("Remove exact duplicate inspections (same license, address, date, type, result, violations); first record kept",
        "(row)", dup.sum(), "inspection ids 58318 to 58324 (Kendall College, same day)", "1 row (58318)",
        "Data > Remove Duplicates on those 6 columns")
    df = df[~dup]

    keep = ["inspection_id", "inspection_date", "facility_name", "aka_name", "license_no", "facility_type_raw",
            "facility_category", "risk_level", "risk_label", "address", "city", "state", "zip", "latitude",
            "longitude", "inspection_type", "inspection_type_raw", "result", "violation_count", "data_flags"]
    clean_df = df[keep].copy()
    clean_df["inspection_id"] = clean_df["inspection_id"].astype(int)
    clean_df["zip"] = clean_df["zip"].astype("string")

    # ---- violations long table
    rows = []
    for iid, v in zip(df["inspection_id"], df["violations"]):
        if pd.isna(v):
            continue
        for part in re.split(r" \| (?=\d+\. )", v):
            m = re.match(r"\s*(\d+)\.\s*(.*?)(?:\s+-\s+Comments:\s*(.*))?$", part, flags=re.S)
            if not m:
                continue
            rows.append(dict(inspection_id=int(iid), violation_no=int(m.group(1)),
                             violation_title=collapse(pd.Series([m.group(2)]))[0],
                             inspector_comment=collapse(pd.Series([m.group(3) or ""]))[0] or None))
    viol_df = pd.DataFrame(rows)
    return clean_df, viol_df, removed, pd.DataFrame(LOG), n0


def main():
    raw = pd.read_csv(RAW, dtype=str)
    clean_df, viol_df, removed, log_df, n0 = clean(raw)
    OUT.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(OUT / "inspections_clean.csv", index=False, date_format="%Y-%m-%d")
    viol_df.to_csv(OUT / "violations_long.csv", index=False)
    removed.to_csv(OUT / "removed_duplicates.csv", index=False, date_format="%Y-%m-%d")
    log_df.to_csv(OUT / "change_log.csv", index=False)
    print(f"raw rows {n0} -> clean rows {len(clean_df)}; duplicates removed {len(removed)}; "
          f"violation rows {len(viol_df)}")


if __name__ == "__main__":
    main()
