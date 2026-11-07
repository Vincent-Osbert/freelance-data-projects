from pathlib import Path

import pandas as pd
import pytest

CLEAN = Path(__file__).resolve().parents[1] / "data" / "clean"


@pytest.fixture(scope="module")
def data():
    return (pd.read_csv(CLEAN / "invoices.csv", dtype={"InvoiceNo": str}),
            pd.read_csv(CLEAN / "products.csv", dtype={"StockCode": str}),
            pd.read_csv(CLEAN / "customers.csv"),
            pd.read_csv(CLEAN / "change_log.csv"))


def test_row_accounting(data):
    log = data[3]
    assert log.rows_removed.sum() + log.rows_left.iloc[-1] == 541_909
    assert (log.rows_left.shift(1).fillna(541_909) - log.rows_removed == log.rows_left).all()


def test_twelve_full_months(data):
    inv = data[0]
    assert sorted(inv.Month.unique()) == [f"2010-12"] + [f"2011-{m:02d}" for m in range(1, 12)]


def test_invoices_unique_and_positive(data):
    inv = data[0]
    assert inv.InvoiceNo.is_unique
    assert not inv.InvoiceNo.str.startswith("C").any()
    assert (inv.Revenue > 0).all() and (inv.Units > 0).all()


def test_tables_reconcile(data):
    inv, prod, cust, _ = data
    assert inv.Revenue.sum() == pytest.approx(prod.Revenue.sum(), abs=1)
    registered = inv[inv.CustomerType == "Registered"]
    assert registered.Revenue.sum() == pytest.approx(cust.Revenue.sum(), abs=1)
    assert len(registered) == cust.Orders.sum()


def test_guest_means_no_customer_id(data):
    inv = data[0]
    assert inv.loc[inv.CustomerType == "Guest", "CustomerID"].isna().all()
    assert inv.loc[inv.CustomerType == "Registered", "CustomerID"].notna().all()
