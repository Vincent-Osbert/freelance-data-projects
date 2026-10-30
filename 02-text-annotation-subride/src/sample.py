"""Draw the evaluation sample and write a blind annotation file.

Usage (from the project folder):
    python src/sample.py

The sample has 150 reviews drawn at random from all 1,338 (an unbiased estimate of
quality) plus 50 reviews on which the two original annotators disagreed (the hard cases).
The blind file shows only an id, the app and the review text. Labels and strata go to a
separate key file that is not read until the relabel is finished.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
OUT = ROOT / "data" / "output"
SEED = 2026


def main():
    pa = pd.read_csv(SRC / "subride_per_annotator.csv")
    fin = pd.read_csv(SRC / "subride_final.csv")[["review", "label"]]
    df = pa.merge(fin, on="review", validate="1:1").rename(
        columns={"1st_annotator_label": "a1", "2nd_annotator_label": "a2", "label": "final"})
    df["row_id"] = range(len(df))

    rand = df.sample(150, random_state=SEED)
    hard_pool = df[(df.a1 != df.a2) & ~df.row_id.isin(rand.row_id)]
    hard = hard_pool.sample(50, random_state=SEED)
    sample = pd.concat([rand.assign(stratum="random"), hard.assign(stratum="hard")])
    sample = sample.sample(frac=1, random_state=SEED).reset_index(drop=True)
    sample["sample_id"] = [f"S{i:03d}" for i in range(1, len(sample) + 1)]

    OUT.mkdir(parents=True, exist_ok=True)
    sample[["sample_id", "app", "review"]].to_csv(OUT / "blind_sample.csv", index=False)
    sample[["sample_id", "row_id", "stratum", "score", "app", "review", "a1", "a2", "final"]].to_csv(
        OUT / "sample_key.csv", index=False)
    print(sample.stratum.value_counts().to_dict(), "wrote blind_sample.csv and sample_key.csv")


if __name__ == "__main__":
    main()
