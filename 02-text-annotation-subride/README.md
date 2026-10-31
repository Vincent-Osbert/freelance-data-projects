# Text annotation QA: Indonesian ride-hailing reviews

How good are the labels in a public Indonesian text dataset, and where exactly do they go wrong? This project writes annotation guidelines, relabels a sample blind, measures agreement, and groups every disagreement by reason.

**Deliverable:** [`deliverable/SubRide_Annotation_QA.xlsx`](deliverable/SubRide_Annotation_QA.xlsx) (guidelines, 200 labelled reviews, agreement tables, 48 disagreements queued for adjudication, 40 model-flagged suspect labels)
**Write-up:** [`docs/AGREEMENT_REPORT.md`](docs/AGREEMENT_REPORT.md) · **Guidelines:** [`docs/ANNOTATION_GUIDELINES.md`](docs/ANNOTATION_GUIDELINES.md)

## AI disclosure

The relabel was produced with an LLM (Claude) following the written guidelines, blind to every existing label. The 48 reviews where it disagrees with the published label carry an LLM-proposed adjudication, which the project author (native Indonesian speaker) reviewed and accepted unchanged (sheet Disagreements, column `human_review`). That corrects 46 of 200 published labels (23%), 30 of 150 in the random sample (20%, 95% CI 14% to 27%). The kappa figures below are pre-adjudication.

## Source

SubRide: Subjectivity Detection in Ride-Hailing App Reviews. Arifin et al., *Data in Brief* (2025), Mendeley Data, [doi:10.17632/3gsbkm8p8r.2](https://doi.org/10.17632/3gsbkm8p8r.2), licence CC BY 4.0. 1,338 Google Play reviews of Gojek, Grab and Maxim, labelled Subjective (1) or Objective (0) by two annotators. The unmodified source CSVs are in `data/source/`. Changes in this repository: sampling, relabelling and analysis only; source labels are not edited.

## Findings

| Result | Number |
|---|---|
| Original two annotators, all 1,338 reviews | kappa 0.672, 88.0% agreement |
| Published label equals annotator 1 when the annotators disagreed | 145 of 161 (90%) |
| Relabel vs published, 150 random reviews | kappa 0.566 (95% CI 0.426 to 0.689), 79.3% agreement |
| Relabel disagrees, direction | 32 said Objective vs published Subjective; 16 the reverse (of 200) |
| Lowest-agreement reason codes | mixed fact-led reviews 57%, event reports 62% |
| Reviews where a text model strongly opposes the published label | 22 in my sample; I disagree on 14 of them (64%) vs 19% elsewhere |

1. The "label after discussion" is effectively annotator 1's label; annotator 2 is far more liberal with Subjective (81.7% vs 71.0%).
2. The biggest source of disagreement is a fact stated inside an emotional complaint. My guideline calls it Objective, the published labels call it Subjective. A guideline v2 that settles the case is proposed in the report but not yet tested.
3. Some clearly positive reviews are published as Objective. Those and the model-flagged rows are the best correction candidates (`data/output/noise_flags.csv`).

## Method

1. `docs/ANNOTATION_GUIDELINES.md` v1 was written before the sample was drawn.
2. `src/sample.py` draws 150 random reviews plus 50 where the original annotators disagreed, and writes a blind file (id, app, text only).
3. The blind file was labelled with one reason code per review (`data/output/relabel_pass1.txt`).
4. `src/agreement.py` computes Cohen's kappa with a bootstrap interval, the confusion matrix, agreement by reason code, and a TF-IDF + logistic regression out-of-fold model to flag suspect labels across all 1,338 reviews.

```bash
pip install -r ../requirements.txt
python src/sample.py        # only to regenerate the sample
python src/agreement.py     # metrics, disagreements, noise flags
python src/build_workbook.py
pytest tests                # 6 checks
```

## Limits

One labeller (an LLM), adjudication by confirming the LLM's proposals (anchoring possible), n = 150 for the headline kappa (interval about 0.26 wide), and 15% of the dataset reviewed by hand. The report lists them in full.
