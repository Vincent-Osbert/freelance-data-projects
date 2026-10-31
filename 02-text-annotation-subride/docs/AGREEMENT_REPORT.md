# Agreement report

All numbers come from `data/output/metrics.json` (written by `src/agreement.py`) and are re-checked by `tests/test_annotation.py`.

## Setup

- Data: SubRide, 1,338 Indonesian reviews of Gojek, Grab and Maxim, labelled Subjective (1) or Objective (0) by two annotators and then reconciled.
- Sample: 200 reviews. 150 drawn at random (an unbiased estimate), 50 drawn from the 161 reviews where the two original annotators disagreed (hard cases).
- Relabel: done blind. The labeller saw only the review text, never a label, a score or the app rating. Guidelines v1 were written before the sample was drawn. The labeller was an LLM (Claude) working from the guidelines; the human adjudication step is still open (see Limits).

## Result 1: the published label is mostly annotator 1

| Comparison (all 1,338 reviews) | Cohen's kappa | Raw agreement |
|---|---|---|
| Annotator 1 vs annotator 2 | 0.672 | 88.0% |
| Annotator 1 vs published | 0.971 | n/a |
| Annotator 2 vs published | 0.701 | n/a |

When the two annotators disagreed (161 reviews), the published label equals annotator 1 in 145 of them (90%). Annotator 2 marks 81.7% of reviews Subjective against 71.0% for annotator 1, so the "agreement after discussion" step behaves like "accept annotator 1". A model trained on these labels inherits annotator 1's taste.

## Result 2: relabel vs published, 150 random reviews

| | Value |
|---|---|
| Raw agreement | 79.3% |
| Cohen's kappa | 0.566 (95% bootstrap CI 0.426 to 0.689) |
| Original annotators on the same 150 | kappa 0.642, 86.7% |
| Subjective share: relabel / published | 56% / 70% |

Confusion (rows = relabel, columns = published): I said Objective and the published label says Subjective on 26 reviews; the reverse happens on 5. So the gap is one-directional: my guidelines call more reviews Objective.

On the 50 hard cases the two annotators disagree by construction, so kappa between them is meaningless. The relabel matches annotator 1 on 74% of them and annotator 2 on 26%; the published label matches annotator 1 on 84%.

## Result 3: where the disagreements sit

48 of 200 reviews disagree with the published label (32 where I said Objective, 16 where I said Subjective).

| Reason code | Reviews | Agreement with published |
|---|---|---|
| MIXED_FACT | 23 | 57% |
| FACT_EVENT | 24 | 62% |
| MIXED_OPINION | 15 | 67% |
| FACT_NUMBER | 28 | 75% |
| FACT_DEFECT | 28 | 79% |
| OPINION_ANGER | 14 | 86% |
| REQUEST | 14 | 86% |
| VAGUE | 28 | 86% |
| OPINION_PRAISE | 26 | 88% |

Reading it:

1. **Facts wrapped in emotion.** All 32 reviews where I said Objective and the published label says Subjective carry a fact code (event, number, defect or mixed-fact). Most state a number or event inside an emotional frame, for example "saya bayar 13rb tapi yang diterima ternyata cuma 8rb" followed by a plea to the company. My rule 5 labelled these Objective. My reading is that the published labels treat the writer's evaluative stance as decisive; that is an interpretation of 32 cases, not something the dataset states.
2. **Probable label errors in the other direction.** Several clearly positive reviews carry the published label Objective, for example "sangat membantu ... tarif nya terjangkau" and "very good ... tarif murah ... sangat membantu". The text model below flags the same kind of rows.
3. **No star-rating pattern.** Agreement with the published label moves between 0.67 and 0.88 across 1 to 5 stars with no trend, so the disagreements are not driven by how unhappy the writer was.

## Result 4: model-flagged suspects across all 1,338

A TF-IDF + logistic regression model (5-fold, out-of-fold probabilities, macro F1 0.699, a sanity baseline and nothing more) was used to find published labels it opposes strongly. `data/output/noise_flags.csv` lists the top 40: 26 published Objective that read as opinion or praise, 14 published Subjective that read as a concrete defect.

Cross-check against my relabel: in my sample, 22 reviews have a model probability of at least 0.7 against the published label. I also disagree with the published label on 14 of them (64%), against 19.1% on the remaining rows. Two independent signals point at the same rows, so those rows are the best candidates for correction.

## Proposed guideline v2 (not yet tested)

- Replace rule 5 with: a review is Subjective when it contains an evaluative or emotional stance, even if it also carries a number or event. Label Objective only for neutral reports, questions and requests that describe a concrete malfunction.
- Add a praise-first rule: any review whose main content is thanks or praise is Subjective, whatever it mentions about price or time.
- Validate v2 on a fresh blind sample before using it. Running it on the current 200 would be contaminated, so I did not.

## Provisional adjudication (LLM-proposed, not yet human-reviewed)

For each of the 48 disagreements the same LLM re-read the review and proposed a label (`data/output/adjudication_proposals.csv`, prefilled in the workbook with `human_review = pending review`). The proposal keeps my relabel in 46 of 48 cases and moves to the published label in 2. If it were accepted as is, 46 of the 200 published labels (23%) would be corrected, 30 of them among the 150 random reviews (20%).

This is not an independent check: the proposer and the relabeller are the same model, so the kappa between the proposal and the published label (0.577 on the 150 random) repeats the first result and is not reported as a finding. The number that matters is the share of corrections a native speaker confirms. Until a human sets `human_review` to confirmed or changed on all 48 rows, treat everything here as pre-adjudication.

## Limits

- One labeller, and it is an LLM, not a native-speaker human. The 48 disagreements carry an LLM-proposed adjudication in `deliverable/SubRide_Annotation_QA.xlsx` (sheet Disagreements) that a native speaker still has to confirm or change (column `human_review`). Every figure above is pre-adjudication.
- n = 150 gives a kappa interval of about 0.26 wide. Differences smaller than that are not evidence.
- The sample is 15% of the dataset; findings about the other 85% rest on the model flags, not on manual review.
- The English translations that ship with the dataset contain broken characters and were not used.
