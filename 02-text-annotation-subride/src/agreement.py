"""Compare the blind relabel with the published labels and write the QA outputs.

Usage (from the project folder, after src/sample.py and the relabel file exist):
    python src/agreement.py

Inputs : data/output/sample_key.csv, data/output/relabel_pass1.txt, data/source/*.csv
Outputs: data/output/relabel_results.csv, disagreements.csv, noise_flags.csv, metrics.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import cohen_kappa_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "output"
SRC = ROOT / "data" / "source"


def load_relabel():
    rows = []
    for line in (OUT / "relabel_pass1.txt").read_text().split("\n"):
        if line.strip():
            sid, lab, code = line.split()
            rows.append((sid, int(lab), code))
    return pd.DataFrame(rows, columns=["sample_id", "my_label", "reason_code"])


def agreement(df, a, b):
    return dict(n=int(len(df)), raw_agreement=round(float((df[a] == df[b]).mean()), 3),
                kappa=round(float(cohen_kappa_score(df[a], df[b])), 3))


def bootstrap_kappa(df, a, b, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(n):
        s = df.sample(len(df), replace=True, random_state=int(rng.integers(1 << 31)))
        if s[a].nunique() > 1 or s[b].nunique() > 1:
            ks.append(cohen_kappa_score(s[a], s[b]))
    return [round(float(np.percentile(ks, 2.5)), 3), round(float(np.percentile(ks, 97.5)), 3)]


def main():
    key = pd.read_csv(OUT / "sample_key.csv")
    res = key.merge(load_relabel(), on="sample_id", validate="1:1")
    assert len(res) == 200 and res.my_label.isin([0, 1]).all()
    res["agrees_with_final"] = res.my_label == res.final
    res.to_csv(OUT / "relabel_results.csv", index=False)

    m = {}
    rnd, hard = res[res.stratum == "random"], res[res.stratum == "hard"]
    for name, d in [("random_150", rnd), ("hard_50", hard), ("all_200", res)]:
        m[name] = {
            "mine_vs_final": agreement(d, "my_label", "final"),
            "mine_vs_annotator1": agreement(d, "my_label", "a1"),
            "mine_vs_annotator2": agreement(d, "my_label", "a2"),
            "annotator1_vs_annotator2": agreement(d, "a1", "a2"),
            "annotator1_vs_final": agreement(d, "a1", "final"),
            "annotator2_vs_final": agreement(d, "a2", "final"),
            "subjective_share": {"mine": round(float(d.my_label.mean()), 3), "final": round(float(d.final.mean()), 3),
                                 "annotator1": round(float(d.a1.mean()), 3), "annotator2": round(float(d.a2.mean()), 3)},
        }
    m["random_150"]["mine_vs_final"]["kappa_95ci_bootstrap"] = bootstrap_kappa(rnd, "my_label", "final")
    m["random_150"]["confusion_mine_rows_final_cols"] = confusion_matrix(rnd.my_label, rnd.final).tolist()

    dis = res[~res.agrees_with_final].copy()
    dis["direction"] = np.where(dis.my_label == 0, "I said Objective, published Subjective",
                                "I said Subjective, published Objective")
    m["disagreements_by_direction"] = dis.direction.value_counts().to_dict()
    m["disagreements_by_reason_code"] = dis.reason_code.value_counts().to_dict()
    m["agreement_rate_by_reason_code"] = {
        c: {"n": int(len(g)), "agree": round(float(g.agrees_with_final.mean()), 2)}
        for c, g in res.groupby("reason_code")}
    m["agreement_rate_by_score"] = {int(s): round(float(g.agrees_with_final.mean()), 2) for s, g in res.groupby("score")}
    dis[["sample_id", "stratum", "app", "score", "review", "my_label", "reason_code", "a1", "a2", "final", "direction"]
        ].assign(adjudicated_label="", adjudicator_note="").to_csv(OUT / "disagreements.csv", index=False)

    # model-based noise flags over all 1,338 published labels
    pa = pd.read_csv(SRC / "subride_per_annotator.csv")
    fin = pd.read_csv(SRC / "subride_final.csv")[["review", "label"]]
    df = pa.merge(fin, on="review", validate="1:1")
    clf = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                        LogisticRegression(C=3, max_iter=1000, class_weight="balanced"))
    proba = cross_val_predict(clf, df.review, df.label, cv=StratifiedKFold(5, shuffle=True, random_state=0),
                              method="predict_proba")[:, 1]
    df["p_subjective"] = proba.round(3)
    pred = (proba >= 0.5).astype(int)
    m["tfidf_logreg_5fold"] = {"macro_f1": round(float(f1_score(df.label, pred, average="macro")), 3),
                              "note": "sanity baseline only; out-of-fold probabilities used to flag suspicious labels"}
    df["model_conf_against_label"] = np.where(df.label == 1, 1 - df.p_subjective, df.p_subjective)
    flags = df.sort_values("model_conf_against_label", ascending=False).head(40)
    flags[["review", "app", "score", "label", "p_subjective", "model_conf_against_label"]].to_csv(
        OUT / "noise_flags.csv", index=False)
    in_sample = res.merge(df[["review", "model_conf_against_label"]], on="review")
    top_q = in_sample.model_conf_against_label >= 0.7
    m["noise_flag_vs_my_disagreement"] = {
        "sample_rows_where_model_strongly_opposes_published_label": int(top_q.sum()),
        "of_which_i_also_disagree": int((top_q & ~in_sample.agrees_with_final).sum()),
        "my_disagreement_rate_elsewhere": round(float((~in_sample[~top_q].agrees_with_final).mean()), 3)}

    (OUT / "metrics.json").write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
