"""Build the Excel sales dashboard with real PivotTables, slicers and a timeline.

Usage (from the project folder, Windows with Microsoft Excel installed):
    python src/build_dashboard.py

Reads  data/clean/*.csv  (written by src/prepare.py)
Writes deliverable/Online_Retail_Sales_Dashboard.xlsx

Excel itself builds the workbook through COM automation, so the pivots, slicers and
PivotCharts are native Excel objects that refresh like ones made by hand.
"""
from pathlib import Path

import pandas as pd
import pywintypes
import win32com.client as win32

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "deliverable" / "Online_Retail_Sales_Dashboard.xlsx"

# Excel constants
xlDatabase, xlRowField, xlColumnField, xlDataField = 1, 1, 2, 4
xlSum, xlCount, xlAverage = -4157, -4112, -4106
xlDescending, xlTopCount = 2, 1
xlLine, xlBarClustered, xlColumnClustered = 4, 57, 51
xlTimeline, xlValidateList, xlSrcRange, xlYes = 2, 3, 1, 1
EXCEL_EPOCH = pd.Timestamp("1899-12-30")
PIVOT_VERSION = 5  # xlPivotTableVersion15, readable by Excel 2013 and later
GBP = "£#,##0"
GBP2 = "£#,##0.00"
INK, ACCENT, PALE = 0x1C1C1C, 0x5C6F1F, 0xF0F5F7  # BGR order for Excel colours


def write_table(ws, df, name, formats):
    """Write a DataFrame to A1 and turn it into an Excel Table."""
    def cell(v):
        if v is None or (not isinstance(v, str) and pd.isna(v)):
            return None
        if isinstance(v, pd.Timestamp):  # Excel date serial
            return (v - EXCEL_EPOCH).days
        return v.item() if hasattr(v, "item") else v

    values = [list(df.columns)] + [[cell(v) for v in row] for row in df.itertuples(index=False)]
    rng = ws.Range(ws.Cells(1, 1), ws.Cells(len(values), len(df.columns)))
    rng.Value = values
    lo = ws.ListObjects.Add(xlSrcRange, rng, None, xlYes)
    lo.Name = name
    lo.TableStyle = "TableStyleLight9"
    for col, fmt in formats.items():
        lo.ListColumns(col).DataBodyRange.NumberFormat = fmt
    ws.Columns.AutoFit()
    ws.Activate()
    ws.Application.ActiveWindow.SplitRow = 1
    ws.Application.ActiveWindow.FreezePanes = True
    return lo


def add_pivot(cache, ws, cell, name, rows=(), cols=(), values=()):
    pt = cache.CreatePivotTable(ws.Range(cell), name)
    pt.RowAxisLayout(1)  # tabular form
    pt.HasAutoFormat = False  # keep the dashboard column widths on refresh
    pt.ShowTableStyleRowStripes = False
    pt.TableStyle2 = "PivotStyleLight16"
    for f in rows:
        pt.PivotFields(f).Orientation = xlRowField
    for f in cols:
        pt.PivotFields(f).Orientation = xlColumnField
    for field, func, caption, fmt in values:
        df = pt.AddDataField(pt.PivotFields(field), caption, func)
        df.NumberFormat = fmt
    return pt


def place_chart(ws, kind, pt, cell_tl, cell_br, title):
    tl, br = ws.Range(cell_tl), ws.Range(cell_br)
    shp = ws.Shapes.AddChart2(-1, kind, tl.Left, tl.Top, br.Left - tl.Left, br.Top - tl.Top)
    ch = shp.Chart
    ch.SetSourceData(pt.TableRange1)
    ch.HasTitle = True
    ch.ChartTitle.Text = title
    ch.HasLegend = False
    ch.Axes(2).TickLabels.NumberFormat = '£#,##0,"k"'
    try:
        ch.ShowAllFieldButtons = False
    except pywintypes.com_error:
        pass
    return ch


def main():
    inv = pd.read_csv(CLEAN / "invoices.csv", parse_dates=["Date"], dtype={"InvoiceNo": str})
    prod = pd.read_csv(CLEAN / "products.csv", dtype={"StockCode": str})
    cust = pd.read_csv(CLEAN / "customers.csv", parse_dates=["FirstOrder", "LastOrder"])
    log = pd.read_csv(CLEAN / "change_log.csv")
    inv["CustomerID"] = inv["CustomerID"].astype("Int64")

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible, xl.DisplayAlerts, xl.ScreenUpdating = False, False, False
    wb = xl.Workbooks.Add()
    while wb.Worksheets.Count < 6:
        wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
    names = ["Dashboard", "Customer_Lookup", "Invoices", "Products", "Customers", "Notes"]
    for ws, n in zip(wb.Worksheets, names):
        ws.Name = n
    dash, look, s_inv, s_prod, s_cust, notes = (wb.Worksheets(n) for n in names)

    try:
        write_table(s_inv, inv, "tblInvoices", {"Date": "dd mmm yyyy", "Revenue": GBP2})
        write_table(s_prod, prod, "tblProducts", {"Revenue": GBP2, "AvgPrice": GBP2})
        write_table(s_cust, cust, "tblCustomers", {"FirstOrder": "dd mmm yyyy", "LastOrder": "dd mmm yyyy",
                                                   "Revenue": GBP2, "AvgOrder": GBP2})

        # ---------------- Dashboard ----------------
        dash.Activate()
        xl.ActiveWindow.DisplayGridlines = False
        dash.Cells.Font.Name = "Calibri"
        dash.Columns("A").ColumnWidth = 2
        dash.Range("B1").Value = "Online Retail: 12-month sales dashboard"
        dash.Range("B1").Font.Size, dash.Range("B1").Font.Bold = 20, True
        dash.Range("B2").Value = ("UK online gift retailer, Dec 2010 - Nov 2011, prices in GBP. "
                                  "Click the slicers or drag the timeline: every number below updates.")
        dash.Range("B2").Font.Color = 0x666666

        inv_cache = wb.PivotCaches().Create(xlDatabase, "tblInvoices", PIVOT_VERSION)
        prod_cache = wb.PivotCaches().Create(xlDatabase, "tblProducts", PIVOT_VERSION)

        # KPI pivot sits out of the way; the tiles read it with GETPIVOTDATA
        kpi = add_pivot(inv_cache, dash, "AA4", "pvKPI", values=[
            ("Revenue", xlSum, "Revenue ", GBP), ("InvoiceNo", xlCount, "Orders", "#,##0"),
            ("Revenue", xlAverage, "Avg order ", GBP2), ("Units", xlSum, "Units ", "#,##0")])
        for col, width in {"A": 2, "B": 36, "C": 12, "D": 12, "E": 12}.items():
            dash.Columns(col).ColumnWidth = width
        dash.Columns("F:X").ColumnWidth = 10
        tiles = [("B12:B13", "Revenue", '=GETPIVOTDATA("Revenue ",$AA$4)', GBP),
                 ("C12:D13", "Orders", '=GETPIVOTDATA("Orders",$AA$4)', "#,##0"),
                 ("F12:H13", "Average order", '=GETPIVOTDATA("Avg order ",$AA$4)', GBP2),
                 ("J12:L13", "Units sold", '=GETPIVOTDATA("Units ",$AA$4)', "#,##0")]
        for addr, label, formula, fmt in tiles:
            box = dash.Range(addr)
            box.Interior.Color = PALE
            head, value = box.Rows(1), box.Rows(2)
            head.Merge(); value.Merge()
            head.Cells(1, 1).Value = label
            head.Font.Color = 0x666666
            value.Cells(1, 1).Formula = formula
            value.NumberFormat = fmt
            value.Font.Size, value.Font.Bold = 18, True
            value.HorizontalAlignment = -4131  # left
        dash.Rows(13).RowHeight = 28
        dash.Rows("4:11").RowHeight = 17  # room for the slicers

        pv_month = add_pivot(inv_cache, dash, "B17", "pvMonth", rows=["Month"],
                             values=[("Revenue", xlSum, "Revenue (GBP)", GBP)])
        pv_country = add_pivot(inv_cache, dash, "B36", "pvCountry", rows=["Country"],
                               values=[("Revenue", xlSum, "Revenue (GBP)", GBP)])
        fld = pv_country.PivotFields("Country")
        fld.AutoSort(xlDescending, "Revenue (GBP)")
        fld.PivotFilters.Add2(xlTopCount, pv_country.DataFields("Revenue (GBP)"), 10)
        pv_heat = add_pivot(inv_cache, dash, "B54", "pvWeekdayHour", rows=["Weekday"], cols=["Hour"],
                            values=[("InvoiceNo", xlCount, "Orders by weekday and hour", "#,##0")])
        pv_prod = add_pivot(prod_cache, dash, "B68", "pvTopProducts", rows=["Description"],
                            values=[("Revenue", xlSum, "Revenue (GBP)", GBP)])
        fp = pv_prod.PivotFields("Description")
        fp.AutoSort(xlDescending, "Revenue (GBP)")
        fp.PivotFilters.Add2(xlTopCount, pv_prod.DataFields("Revenue (GBP)"), 10)
        for pt in (pv_month, pv_country, pv_heat, pv_prod, kpi):
            pt.ColumnGrand = pt is not pv_heat
            pt.RowGrand = False

        # heatmap colours on the weekday x hour grid
        body = pv_heat.DataBodyRange
        body.FormatConditions.AddColorScale(2)
        body.FormatConditions(1).ColorScaleCriteria(1).FormatColor.Color = 0xFFFFFF
        body.FormatConditions(1).ColorScaleCriteria(2).FormatColor.Color = ACCENT

        place_chart(dash, xlLine, pv_month, "F17", "N33", "Revenue by month")
        place_chart(dash, xlBarClustered, pv_country, "F36", "N51", "Top 10 countries by revenue")
        ch = place_chart(dash, xlBarClustered, pv_prod, "F68", "N84", "Top 10 products by revenue (all year)")
        ch.Axes(1).ReversePlotOrder = True

        # slicers and timeline drive every invoice pivot (shared cache)
        def slicer(cache, name, caption, cell, width, height=120):
            sl = cache.Slicers.Add(dash)
            sl.Name, sl.Caption = name, caption
            sl.Top, sl.Left = dash.Range(cell).Top, dash.Range(cell).Left
            sl.Width, sl.Height = width, height
            return sl

        sc_country = wb.SlicerCaches.Add2(pv_month, "Country", "Slicer_Country")
        slicer(sc_country, "slCountry", "Country", "B4", 190)
        sc_type = wb.SlicerCaches.Add2(pv_month, "CustomerType", "Slicer_CustomerType")
        slicer(sc_type, "slCustomerType", "Customer type", "C4", 140)
        sc_time = wb.SlicerCaches.Add2(pv_month, "Date", "NativeTimeline_Date", xlTimeline)
        slicer(sc_time, "slDate", "Order date", "F4", 520)
        for sc in (sc_country, sc_type, sc_time):
            for pt in (pv_country, pv_heat, kpi):
                sc.PivotTables.AddPivotTable(pt)
        dash.Columns("Z:AF").Hidden = True  # helper pivot behind the KPI tiles
        dash.Range("B66").Value = "Product ranking uses the full year and does not follow the slicers."
        dash.Range("B66").Font.Italic, dash.Range("B66").Font.Color = True, 0x666666

        # ---------------- Customer lookup ----------------
        look.Activate()
        xl.ActiveWindow.DisplayGridlines = False
        look.Columns("A").ColumnWidth = 2
        look.Columns("B").ColumnWidth = 30
        look.Columns("C").ColumnWidth = 18
        look.Range("B1").Value = "Customer lookup"
        look.Range("B1").Font.Size, look.Range("B1").Font.Bold = 18, True
        look.Range("B2").Value = "Pick a customer ID in the yellow cell (dropdown). Everything else is formulas."
        look.Range("B2").Font.Color = 0x666666
        look.Range("B4").Value = "Customer ID"
        look.Range("C4").Value = int(cust.CustomerID.iloc[0])
        look.Range("C4").Interior.Color = 0x99FFFF
        look.Range("C4").Font.Bold = True
        dv = look.Range("C4").Validation
        dv.Delete()
        dv.Add(xlValidateList, 1, 1, '=INDIRECT("tblCustomers[CustomerID]")')
        fields = [("Country", "tblCustomers[Country]", "@"),
                  ("First order", "tblCustomers[FirstOrder]", "dd mmm yyyy"),
                  ("Last order", "tblCustomers[LastOrder]", "dd mmm yyyy"),
                  ("Orders", "tblCustomers[Orders]", "#,##0"),
                  ("Revenue", "tblCustomers[Revenue]", GBP2),
                  ("Average order", "tblCustomers[AvgOrder]", GBP2)]
        for i, (label, ref, fmt) in enumerate(fields, start=5):
            look.Range(f"B{i}").Value = label
            look.Range(f"C{i}").Formula2 = f'=XLOOKUP($C$4,tblCustomers[CustomerID],{ref},"not found")'
            look.Range(f"C{i}").NumberFormat = fmt
        look.Range("B11").Value = "Revenue rank (of all customers)"
        look.Range("C11").Formula2 = '=IFERROR(MATCH($C$4,tblCustomers[CustomerID],0)&" of "&ROWS(tblCustomers[CustomerID]),"-")'
        look.Range("B13").Value = "Month"
        look.Range("C13").Value = "Revenue"
        look.Range("D13").Value = "Orders"
        look.Range("B13:D13").Font.Bold = True
        months = sorted(inv.Month.unique())
        for i, m in enumerate(months, start=14):
            look.Range(f"B{i}").NumberFormat = "@"
            look.Range(f"B{i}").Value = m
            look.Range(f"C{i}").Formula = f"=SUMIFS(tblInvoices[Revenue],tblInvoices[CustomerID],$C$4,tblInvoices[Month],B{i})"
            look.Range(f"D{i}").Formula = f"=COUNTIFS(tblInvoices[CustomerID],$C$4,tblInvoices[Month],B{i})"
            look.Range(f"C{i}").NumberFormat = GBP2
        last = 13 + len(months)
        look.Range(f"C14:C{last}").FormatConditions.AddDatabar()
        tl, br = look.Range("F4"), look.Range(f"N{last}")
        shp = look.Shapes.AddChart2(-1, xlColumnClustered, tl.Left, tl.Top, br.Left - tl.Left, br.Top - tl.Top)
        shp.Chart.SetSourceData(look.Range(f"B13:C{last}"))
        shp.Chart.HasTitle, shp.Chart.HasLegend = True, False
        shp.Chart.ChartTitle.Text = "This customer's revenue by month"
        shp.Chart.Axes(2).TickLabels.NumberFormat = GBP

        # ---------------- Notes ----------------
        notes.Columns("A").ColumnWidth = 2
        notes.Columns("B").ColumnWidth = 60
        notes.Columns("C").ColumnWidth = 14
        notes.Columns("D").ColumnWidth = 12
        lines = [
            ("About this workbook", True),
            ("Source: Online Retail, UCI Machine Learning Repository (dataset 352), Daqing Chen, 2015. Licence CC BY 4.0.", False),
            ("A UK online gift retailer, many customers are wholesalers. Prices are in GBP.", False),
            ("Period: 1 Dec 2010 to 30 Nov 2011 (12 full months; the raw file stops on 9 Dec 2011).", False),
            ("", False),
            ("How to use and refresh", True),
            ("Dashboard: click Country or Customer type, or drag the timeline. Clear a slicer with its funnel icon.", False),
            ("New data: paste rows into the Invoices / Products / Customers tables, then Data > Refresh All.", False),
            ("Customer_Lookup: pick a customer ID in the yellow cell; the rest is XLOOKUP, SUMIFS and COUNTIFS.", False),
            ("", False),
            ("Things to know", True),
            ("Guest = invoice with no customer ID. It is a real sale, but it cannot be tied to a customer.", False),
            ("Country is the one on the invoice. A few customers order from more than one country.", False),
            ("Average order = revenue per invoice. Wholesale invoices make it higher than a typical shop basket.", False),
            ("There are no orders on Saturdays in this data, so the heatmap has no Saturday row.", False),
            ("Product ranking covers the whole year and does not follow the slicers (it has its own data table).", False),
            ("", False),
            ("Rows removed from the raw file (541,909 lines)", True),
        ]
        for i, (text, bold) in enumerate(lines, start=1):
            notes.Range(f"B{i}").Value = text
            notes.Range(f"B{i}").Font.Bold = bold
            if bold:
                notes.Range(f"B{i}").Font.Size = 13
        r0 = len(lines) + 1
        notes.Range(f"B{r0}:D{r0}").Value = ["Rule", "Rows removed", "Rows left"]
        notes.Range(f"B{r0}:D{r0}").Font.Bold = True
        for j, row in enumerate(log.itertuples(index=False), start=r0 + 1):
            notes.Range(f"B{j}:D{j}").Value = [row.rule, int(row.rows_removed), int(row.rows_left)]
            notes.Range(f"C{j}:D{j}").NumberFormat = "#,##0"
        notes.Range(f"B{r0}:D{r0 + len(log)}").WrapText = False

        wb.RefreshAll()
        dash.Activate()
        dash.Range("A1").Select()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        if OUT.exists():
            OUT.unlink()
        wb.SaveAs(str(OUT), 51)  # xlOpenXMLWorkbook
        print("saved", OUT)
    finally:
        wb.Close(False)
        xl.Quit()


if __name__ == "__main__":
    main()
