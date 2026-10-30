# Annotation Guidelines v1: Subjective vs Objective (Indonesian ride-hailing reviews)

Written before looking at any sampled review. The examples below are my own illustrative sentences, not rows from the dataset.

## Task

Label each review with one of two classes.

| Label | Name | One-line test |
|---|---|---|
| 1 | Subjective | The text is mainly an opinion, feeling, praise, or vague judgement. |
| 0 | Objective | The text is mainly a verifiable event, a fact about the app or the trip, or a concrete defect. |

The definitions follow the SubRide paper (Arifin et al., Data in Brief, 2025). Rules 3 to 7 are my own readings of cases the paper leaves open.

## Decision order

Apply the first rule that fits.

1. **Is the main point a verifiable event or a measurable problem?** Something that happened and could be checked from logs, receipts, or screenshots: app crash, login failure, payment not credited, wrong fare, driver cancelled, no driver found after a stated wait, GPS pointing to the wrong place. Label **0**.
2. **Is the main point an opinion, emotion, or rating of quality?** Praise ("mantap"), anger ("parah banget"), taste, general satisfaction. Label **1**.
3. **Mixed review.** Label by the main intent: if more than half of the content (or the closing sentence that states what the user wants) is a checkable fact, label 0; otherwise 1.
4. **Vague measures are opinion.** "Mahal", "lama", "jauh", "sering", "kadang" with no number or concrete event are 1. The same sentence with a number or event ("nunggu 2 jam", "tarif naik dari 15 ribu jadi 28 ribu") is 0.
5. **Emotion on top of a fact.** "Aplikasi error terus, kesel banget" states a defect (0 by rule 1); the anger does not flip it to 1, unless the defect is only mentioned in passing and the text is mostly venting.
6. **Requests and demands** ("tolong perbaiki", "mohon dibalas") are 1 unless they contain the concrete event they respond to, in which case apply rules 1 and 3.
7. **Questions** ("kenapa saldo tidak masuk?") are 0 when they report a concrete situation, 1 when rhetorical or emotional.

If a review cannot be labelled after rules 1 to 7, mark it **unsure** and keep it out of agreement statistics. Do not force a label.

## Reason codes

Every label carries one code so disagreements can be grouped later.

| Code | Meaning | Typical label |
|---|---|---|
| FACT_EVENT | A specific event or action with context | 0 |
| FACT_DEFECT | App or payment malfunction | 0 |
| FACT_NUMBER | Number or time that makes a complaint checkable | 0 |
| OPINION_PRAISE | Praise or general satisfaction | 1 |
| OPINION_ANGER | Anger or frustration without a checkable event | 1 |
| VAGUE | Vague measure ("mahal", "lama") | 1 |
| REQUEST | Request or demand with no event | 1 |
| MIXED_FACT | Mixed, fact dominates | 0 |
| MIXED_OPINION | Mixed, opinion dominates | 1 |
| UNSURE | Cannot decide | none |

## Worked examples (illustrative)

| Review | Label | Code | Why |
|---|---|---|---|
| "Aplikasinya error terus pas bayar pakai gopay, saldo kepotong tapi order tidak jalan" | 0 | FACT_DEFECT | payment defect, checkable |
| "Drivernya ramah banget, mobil bersih, mantap" | 1 | OPINION_PRAISE | praise |
| "Mahal banget sekarang" | 1 | VAGUE | no number |
| "Tarif kemarin 18 ribu, sekarang 31 ribu untuk rute yang sama" | 0 | FACT_NUMBER | checkable fare |
| "Driver batalin 3 kali, nunggu 1 jam, kesel parah" | 0 | MIXED_FACT | events dominate the anger |
| "Tolong diperbaiki aplikasinya" | 1 | REQUEST | no event |
| "Kesel, jelek, gak bagus lagi" | 1 | OPINION_ANGER | venting only |

## Known weak spots

- Rule 5 is a judgement call; expect most disagreements between careful annotators here.
- Short reviews ("bagus") are easy; long angry reviews that bury one fact are hard.
- Sarcasm is labelled by its literal intent only when the intent is clear; otherwise **unsure**.
- The star rating is not shown to the annotator, so it cannot leak into the label.
