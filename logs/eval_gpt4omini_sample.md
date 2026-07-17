# Evaluation report — Full AFAM

**Total alerts**: 6
**Total wall-clock**: 90.3s (avg 14.9s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 100.0%  |
| Lenient accuracy (incl. alt_ok_verdicts)  | 100.0%  |
| Confidence calibrated (in expected range) | 0.0%    |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category       |   N | Strict   | Lenient   |   Rounds | Verdicts          |
|----------------|-----|----------|-----------|----------|-------------------|
| A_obvious_gang |   6 | 100%     | 100%      |        5 | fraud_confirmed=6 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   0 | —            |
| [0.70,0.85)  |   6 | 100%         |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 6       |
| Avg recall on holdout     | 60.8%   |
| Avg FP-rate on holdout    | 0.00%   |
| Avg precision             | 100.0%  |
