"""Prepare the UCI Online Retail data for the Excel sales dashboard.

Usage (from the project folder):
    python src/prepare.py path/to/online_retail.csv

The raw file is not stored in this repo (46 MB). Download "Online Retail" from the
UCI Machine Learning Repository (dataset 352, CC BY 4.0) and save the sheet as CSV.

Writes data/clean/invoices.csv    one row per sales invoice
       data/clean/products.csv    one row per product
       data/clean/customers.csv   one row per registered customer
       data/clean/change_log.csv  every rule and how many rows it removed
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "clean"
START, END = "2010-12-01", "2011-12-01"  # 12 full months; December 2011 stops on the 9th
WEEKDAYS = ["1 Mon", "2 Tue", "3 Wed", "4 Thu", "5 Fri", "6 Sat", "7 Sun"]


def main(raw_path):
    raw = pd.read_csv(raw_path, dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str})
    raw["InvoiceDate"] = pd.to_datetime(raw["InvoiceDate"])
    log, d = [], raw.copy()

    def drop(rule, mask):
        nonlocal d
        log.append({"rule": rule, "rows_removed": int(mask.sum()), "rows_left": int((~mask).sum())})
        d = d[~mask]

    drop("Outside Dec 2010 - Nov 2011 (keep 12 full months)",
         (d.InvoiceDate < START) | (d.InvoiceDate >= END))
    drop("Cancelled invoice (number starts with C)", d.InvoiceNo.str.startswith("C"))
    drop("Quantity zero or negative (stock adjustments)", d.Quantity <= 0)
    drop("Unit price zero or negative", d.UnitPrice <= 0)
    drop("Not a product (postage, fees, manual lines, samples)", ~d.StockCode.str.match(r"^\d{5}"))
    drop("Exact duplicate line", d.duplicated())

    d = d.assign(Revenue=(d.Quantity * d.UnitPrice).round(2),
                 CustomerID=d.CustomerID.str.replace(r"\.0$", "", regex=True),
                 Description=d.Description.fillna("").str.strip().str.upper())

    inv = d.groupby("InvoiceNo").agg(
        InvoiceDate=("InvoiceDate", "first"), Country=("Country", "first"),
        CustomerID=("CustomerID", "first"), Lines=("StockCode", "size"),
        Units=("Quantity", "sum"), Revenue=("Revenue", "sum")).reset_index()
    inv["Date"] = inv.InvoiceDate.dt.normalize()
    inv["Month"] = inv.InvoiceDate.dt.strftime("%Y-%m")
    inv["Weekday"] = inv.InvoiceDate.dt.dayofweek.map(dict(enumerate(WEEKDAYS)))
    inv["Hour"] = inv.InvoiceDate.dt.hour
    inv["CustomerType"] = inv.CustomerID.notna().map({True: "Registered", False: "Guest"})
    inv["Revenue"] = inv.Revenue.round(2)
    inv = inv[["InvoiceNo", "Date", "Month", "Weekday", "Hour", "Country", "CustomerType",
               "CustomerID", "Lines", "Units", "Revenue"]]

    names = d.groupby("StockCode").Description.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "")
    prod = d.groupby("StockCode").agg(Invoices=("InvoiceNo", "nunique"), Units=("Quantity", "sum"),
                                      Revenue=("Revenue", "sum")).reset_index()
    prod.insert(1, "Description", prod.StockCode.map(names))
    prod["AvgPrice"] = (prod.Revenue / prod.Units).round(2)
    prod["Revenue"] = prod.Revenue.round(2)
    prod = prod.sort_values("Revenue", ascending=False)

    reg = inv.dropna(subset=["CustomerID"])
    cust = reg.groupby("CustomerID").agg(
        Country=("Country", lambda s: s.mode().iat[0]), FirstOrder=("Date", "min"),
        LastOrder=("Date", "max"), Orders=("InvoiceNo", "size"), Revenue=("Revenue", "sum")).reset_index()
    cust["AvgOrder"] = (cust.Revenue / cust.Orders).round(2)
    cust["Revenue"] = cust.Revenue.round(2)
    cust = cust.sort_values("Revenue", ascending=False)

    OUT.mkdir(parents=True, exist_ok=True)
    inv.to_csv(OUT / "invoices.csv", index=False, date_format="%Y-%m-%d")
    prod.to_csv(OUT / "products.csv", index=False)
    cust.to_csv(OUT / "customers.csv", index=False, date_format="%Y-%m-%d")
    pd.DataFrame(log).to_csv(OUT / "change_log.csv", index=False)
    print(pd.DataFrame(log).to_string(index=False))
    print(f"invoices {len(inv):,}  products {len(prod):,}  customers {len(cust):,}  "
          f"revenue {inv.Revenue.sum():,.2f}")


if __name__ == "__main__":
    main(sys.argv[1])
