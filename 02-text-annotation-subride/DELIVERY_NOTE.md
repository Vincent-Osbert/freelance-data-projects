# Sample delivery note (what a client receives with the files)

**Files:** `SubRide_Annotation_QA.xlsx` (Guidelines, Labeled_Sample, Agreement, Disagreements, Noise_Flags) and `docs/AGREEMENT_REPORT.md`.

**What I did:** wrote guidelines v1 before seeing data; relabelled 200 reviews blind with an LLM (not by hand) under those guidelines; compared with the published labels.

**What I found:** kappa 0.566 on 150 random reviews (95% CI 0.426 to 0.689). The published consensus equals annotator 1 in 145 of 161 disagreements. 48 of my 200 labels differ from the published ones; most are facts stated inside an emotional complaint.

**What I am unsure about:** all figures are before human adjudication of those 48 cases; n = 150 gives a wide interval; guideline v2 is proposed, not tested.

**Next step if useful:** adjudicate the 48 cases, then test v2 on a fresh blind sample.
