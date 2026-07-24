# Evaluation report — Full AFAM

**Total alerts**: 14
**Total wall-clock**: 160.9s (avg 11.4s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 78.6%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 85.7%   |
| Confidence calibrated (in expected range) | 35.7%   |
| Avg rounds                                | 4.9     |

## Per-category breakdown

| Category          |   N | Strict   | Lenient   |   Rounds | Verdicts                      |
|-------------------|-----|----------|-----------|----------|-------------------------------|
| A_obvious_gang    |   8 | 75%      | 75%       |      5   | fraud_confirmed=6, escalate=2 |
| B_subtle_immature |   6 | 83%      | 100%      |      4.7 | fraud_confirmed=5, escalate=1 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   1 | 100%         |
| [0.70,0.85)  |  10 | 100%         |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 12      |
| Avg recall on holdout     | 68.6%   |
| Avg FP-rate on holdout    | 0.00%   |
| Avg precision             | 100.0%  |

## Wrong cases (need attention)

| Alert    | Category       | Expected        | Actual   |   Conf |   Rounds |
|----------|----------------|-----------------|----------|--------|----------|
| eval_A04 | A_obvious_gang | fraud_confirmed | escalate |      0 |        5 |
| eval_A07 | A_obvious_gang | fraud_confirmed | escalate |      0 |        5 |