"""Build the client-style Excel deliverable for the annotation project.

Usage (from the project folder, after src/agreement.py):
    python src/build_workbook.py
"""
import json
from pathlib import Path

import pandas as pd
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "output"
DEST = ROOT / "deliverable" / "SubRide_Annotation_QA.xlsx"
DEST.parent.mkdir(exist_ok=True)

res = pd.read_csv(OUT / "relabel_results.csv")
dis = pd.read_csv(OUT / "disagreements.csv", keep_default_na=False)
noise = pd.read_csv(OUT / "noise_flags.csv")
m = json.loads((OUT / "metrics.json").read_text())

wb = xlsxwriter.Workbook(DEST)
F = lambda **k: wb.add_format({"font_name": "Calibri", "font_size": 11, **k})
title, h = F(bold=True, font_size=16), F(bold=True, bg_color="#1F3864", font_color="#FFFFFF", border=1, text_wrap=True)
cell, wrap, note = F(border=1, text_wrap=True, valign="top"), F(text_wrap=True, valign="top"), F(italic=True, font_color="#555555", text_wrap=True)
red, green = F(bg_color="#FCE4D6", border=1, text_wrap=True, valign="top"), F(bg_color="#E2EFDA", border=1, text_wrap=True, valign="top")

# --- README
ws = wb.add_worksheet("README")
rd = m["random_150"]
lines = [
    ("Subjectivity labelling QA: Indonesian ride-hailing reviews", title),
    ("", None),
    ("What this is: a worked example of annotation quality control. I wrote guidelines before seeing any data, relabelled "
     "200 reviews blind, measured agreement with the published labels of the SubRide dataset (Arifin et al., Data in Brief 2025, "
     "CC BY 4.0, doi:10.17632/3gsbkm8p8r.2), and grouped every disagreement by reason.", wrap),
    ("", None),
    ("AI disclosure: the relabel was produced with an LLM (Claude) following the written guidelines, blind to all existing labels. "
     "The 48 disagreements are queued for a native-speaker human adjudicator (sheet Disagreements, column adjudicated_label). "
     "Until that is filled, every number here is pre-adjudication.", wrap),
    ("", None),
    (f"Headline: on 150 randomly drawn reviews the relabel agrees with the published label {rd['mine_vs_final']['raw_agreement']:.1%} of the time "
     f"(Cohen's kappa {rd['mine_vs_final']['kappa']}, 95% bootstrap CI {rd['mine_vs_final']['kappa_95ci_bootstrap'][0]} to "
     f"{rd['mine_vs_final']['kappa_95ci_bootstrap'][1]}). The two original annotators agree with each other at kappa "
     f"{rd['annotator1_vs_annotator2']['kappa']} on the same 150.", wrap),
    ("", None),
    ("Sheets: Guidelines | Labeled_Sample | Agreement | Disagreements (to adjudicate) | Noise_Flags (model-flagged suspect labels, all 1,338 rows)", wrap),
]
for i, (t, f) in enumerate(lines):
    if f:
        ws.write(i, 0, t, f)
ws.set_column(0, 0, 140)
for i in (2, 4, 6):
    ws.set_row(i, 62)

# --- Guidelines
ws = wb.add_worksheet("Guidelines")
g = [("Rule", "What to do"),
     ("1", "Verifiable event or measurable problem (crash, payment bug, wrong fare, cancellation with context) is Objective (0)."),
     ("2", "Opinion, emotion, praise, or quality rating is Subjective (1)."),
     ("3", "Mixed review: label by main intent. 0 only if more than half the content, or the closing statement, is a checkable fact."),
     ("4", "Vague measures (mahal, lama, jauh, sering) without a number or event are Subjective."),
     ("5", "Emotion on top of a fact does not flip it to Subjective unless the fact is only mentioned in passing. (Weakest rule; see Agreement.)"),
     ("6", "Requests are Subjective unless they carry the concrete event they respond to."),
     ("7", "Questions are Objective when reporting a concrete situation, Subjective when rhetorical or emotional."),
     ("-", "Cannot decide after rules 1 to 7: mark unsure and exclude from statistics. Full text: docs/ANNOTATION_GUIDELINES.md")]
for i, (a, b) in enumerate(g):
    ws.write(i, 0, a, h if i == 0 else cell)
    ws.write(i, 1, b, h if i == 0 else cell)
ws.set_column(0, 0, 8)
ws.set_column(1, 1, 130)

# --- Labeled sample
ws = wb.add_worksheet("Labeled_Sample")
cols = ["sample_id", "stratum", "app", "review", "my_label", "reason_code", "a1", "a2", "final", "agrees_with_final"]
heads = ["ID", "Stratum", "App", "Review (Indonesian)", "Relabel", "Reason code", "Annotator 1", "Annotator 2", "Published", "Agrees"]
for j, c in enumerate(heads):
    ws.write(0, j, c, h)
for i, r in enumerate(res[cols].itertuples(index=False), start=1):
    for j, v in enumerate(r):
        f = (green if v else red) if cols[j] == "agrees_with_final" else cell
        ws.write(i, j, "yes" if cols[j] == "agrees_with_final" and v else ("no" if cols[j] == "agrees_with_final" else v), f)
ws.set_column(0, 2, 10)
ws.set_column(3, 3, 90)
ws.set_column(4, 9, 13)
ws.freeze_panes(1, 1)
ws.autofilter(0, 0, len(res), len(cols) - 1)

# --- Agreement
ws = wb.add_worksheet("Agreement")
ws.write(0, 0, "Agreement summary (Cohen's kappa and raw agreement)", title)
heads = ["Comparison", "Sample", "n", "Raw agreement", "Kappa", "Note"]
for j, c in enumerate(heads):
    ws.write(2, j, c, h)
rows = []
for key, label in [("random_150", "150 random"), ("hard_50", "50 hard (annotators disagreed)"), ("all_200", "all 200")]:
    for comp, name in [("mine_vs_final", "Relabel vs published"), ("mine_vs_annotator1", "Relabel vs annotator 1"),
                       ("mine_vs_annotator2", "Relabel vs annotator 2"), ("annotator1_vs_annotator2", "Annotator 1 vs 2"),
                       ("annotator1_vs_final", "Annotator 1 vs published"), ("annotator2_vs_final", "Annotator 2 vs published")]:
        a = m[key][comp]
        nt = "annotators disagree by design: kappa not meaningful" if key == "hard_50" and comp in ("annotator1_vs_annotator2", "annotator1_vs_final", "annotator2_vs_final") else ""
        rows.append((name, label, a["n"], a["raw_agreement"], a["kappa"], nt))
for i, r in enumerate(rows, start=3):
    for j, v in enumerate(r):
        ws.write(i, j, v, cell)
r0 = 3 + len(rows) + 1
ws.write(r0, 0, "Where disagreements come from (relabel vs published, all 200)", F(bold=True))
for j, c in enumerate(["Reason code", "n labelled", "agreement with published"]):
    ws.write(r0 + 1, j, c, h)
for i, (c, v) in enumerate(sorted(m["agreement_rate_by_reason_code"].items(), key=lambda kv: kv[1]["agree"]), start=r0 + 2):
    ws.write(i, 0, c, cell)
    ws.write(i, 1, v["n"], cell)
    ws.write(i, 2, v["agree"], cell)
ws.set_column(0, 0, 36)
ws.set_column(1, 1, 30)
ws.set_column(2, 4, 14)
ws.set_column(5, 5, 50)

# --- Disagreements
ws = wb.add_worksheet("Disagreements")
heads = ["ID", "Stratum", "Review (Indonesian)", "Relabel", "Reason code", "Annotator 1", "Annotator 2", "Published", "Direction", "adjudicated_label", "adjudicator_note"]
cols = ["sample_id", "stratum", "review", "my_label", "reason_code", "a1", "a2", "final", "direction"]
for j, c in enumerate(heads):
    ws.write(0, j, c, h)
for i, r in enumerate(dis[cols].itertuples(index=False), start=1):
    for j, v in enumerate(r):
        ws.write(i, j, v, cell)
    ws.write(i, 9, "", F(border=1, bg_color="#FFF2CC"))
    ws.write(i, 10, "", F(border=1, bg_color="#FFF2CC"))
ws.data_validation(1, 9, len(dis), 9, {"validate": "list", "source": ["0", "1", "unsure"]})
ws.set_column(0, 1, 9)
ws.set_column(2, 2, 90)
ws.set_column(3, 7, 11)
ws.set_column(8, 8, 36)
ws.set_column(9, 10, 20)
ws.freeze_panes(1, 1)

# --- Noise flags
ws = wb.add_worksheet("Noise_Flags")
ws.write(0, 0, "Published labels a simple text model opposes most strongly (5-fold out-of-fold, TF-IDF + logistic regression)", F(bold=True))
heads = ["Published label", "P(subjective)", "Stars", "App", "Review (Indonesian)"]
for j, c in enumerate(heads):
    ws.write(2, j, c, h)
for i, r in enumerate(noise.itertuples(index=False), start=3):
    for j, v in enumerate([r.label, r.p_subjective, r.score, r.app, r.review]):
        ws.write(i, j, v, cell)
ws.set_column(0, 3, 14)
ws.set_column(4, 4, 110)
wb.close()
print("wrote", DEST)
