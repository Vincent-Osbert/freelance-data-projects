import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import clean as cl  # noqa: E402

RAW = pd.read_csv(ROOT / "data" / "raw" / "chicago_food_inspections_raw.csv", dtype=str)


@pytest.fixture(scope="module")
def out():
    cl.LOG.clear()
    return cl.clean(RAW)


def test_row_accounting(out):
    c, v, removed, log, n0 = out
    assert n0 == len(RAW) == 6000
    assert len(c) + len(removed) == n0


def test_ids_unique(out):
    assert out[0]["inspection_id"].is_unique


def test_no_whitespace_problems(out):
    c = out[0]
    for col in ["facility_name", "address"]:
        s = c[col].dropna()
        assert (s == s.str.replace(r"\s+", " ", regex=True).str.strip()).all()


def test_city_is_chicago(out):
    assert set(out[0]["city"]) == {"CHICAGO"}


def test_license_zero_removed(out):
    assert not (out[0]["license_no"] == 0).any()


def test_dates_are_dates_in_range(out):
    d = pd.to_datetime(out[0]["inspection_date"])
    assert d.notna().all() and d.min() >= pd.Timestamp("2010-01-01") and d.max() <= pd.Timestamp("2011-12-31")


def test_risk_levels(out):
    assert set(out[0]["risk_level"].dropna()) <= {1, 2, 3}


def test_no_blank_category(out):
    assert out[0]["facility_category"].notna().all()


def test_violation_counts_match_long_table(out):
    c, v = out[0], out[1]
    per = v.groupby("inspection_id").size()
    joined = c.set_index("inspection_id")["violation_count"]
    assert (per == joined.loc[per.index]).all()
    assert joined.drop(per.index).eq(0).all()


def test_removed_rows_are_true_duplicates(out):
    c, removed = out[0], out[2]
    raw = RAW.set_index("inspection_id")
    for _, r in removed.iterrows():
        a, b = raw.loc[str(r["inspection_id"])], raw.loc[str(r["duplicate_of_inspection_id"])]
        assert a["license_"] == b["license_"] and a["inspection_date"] == b["inspection_date"]
        assert a["violations"] == b["violations"] or (pd.isna(a["violations"]) and pd.isna(b["violations"]))
        assert int(r["duplicate_of_inspection_id"]) in set(c["inspection_id"])


def test_rule_counts_logged(out):
    assert (out[3]["rows_changed"] >= 0).all() and len(out[3]) >= 12
