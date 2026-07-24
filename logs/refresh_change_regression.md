# Evaluation report — Full AFAM

**Total alerts**: 2
**Total wall-clock**: 0.1s (avg 0.0s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 100.0%  |
| Lenient accuracy (incl. alt_ok_verdicts)  | 100.0%  |
| Confidence calibrated (in expected range) | 100.0%  |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category       |   N | Strict   | Lenient   |   Rounds | Verdicts          |
|----------------|-----|----------|-----------|----------|-------------------|
| A_obvious_gang |   2 | 100%     | 100%      |        5 | fraud_confirmed=2 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   0 | —            |
| [0.70,0.85)  |   0 | —            |
| [0.85,1.00)  |   2 | 100%         |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 2       |
| Avg recall on holdout     | 32.6%   |
| Avg FP-rate on holdout    | 0.00%   |
| Avg precision             | 100.0%  |
