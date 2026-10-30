import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "output"
CODES = {"FACT_EVENT", "FACT_DEFECT", "FACT_NUMBER", "OPINION_PRAISE", "OPINION_ANGER", "VAGUE", "REQUEST",
         "MIXED_FACT", "MIXED_OPINION"}


def test_source_files_align():
    pa = pd.read_csv(ROOT / "data" / "source" / "subride_per_annotator.csv")
    fin = pd.read_csv(ROOT / "data" / "source" / "subride_final.csv")
    assert len(pa) == len(fin) == 1338
    assert set(pa.review) == set(fin.review)


def test_blind_file_has_no_labels():
    blind = pd.read_csv(OUT / "blind_sample.csv")
    assert list(blind.columns) == ["sample_id", "app", "review"]
    assert blind.sample_id.is_unique and len(blind) == 200


def test_sample_design():
    key = pd.read_csv(OUT / "sample_key.csv")
    assert key.stratum.value_counts().to_dict() == {"random": 150, "hard": 50}
    assert (key[key.stratum == "hard"].a1 != key[key.stratum == "hard"].a2).all()
    assert key.row_id.is_unique


def test_relabel_complete_and_valid():
    r = pd.read_csv(OUT / "relabel_results.csv")
    assert len(r) == 200 and r.my_label.isin([0, 1]).all() and set(r.reason_code) <= CODES
    # a reason code must imply the label direction
    zero = {"FACT_EVENT", "FACT_DEFECT", "FACT_NUMBER", "MIXED_FACT"}
    assert (r[r.reason_code.isin(zero)].my_label == 0).all()
    assert (r[~r.reason_code.isin(zero)].my_label == 1).all()


def test_metrics_reproduce():
    r = pd.read_csv(OUT / "relabel_results.csv")
    m = json.loads((OUT / "metrics.json").read_text())
    rnd = r[r.stratum == "random"]
    assert round(cohen_kappa_score(rnd.my_label, rnd.final), 3) == m["random_150"]["mine_vs_final"]["kappa"]
    assert round((r.my_label == r.final).mean(), 3) == m["all_200"]["mine_vs_final"]["raw_agreement"]


def test_disagreement_sheet_matches():
    r = pd.read_csv(OUT / "relabel_results.csv")
    d = pd.read_csv(OUT / "disagreements.csv")
    assert len(d) == int((r.my_label != r.final).sum())
    assert (d.my_label != d.final).all()
