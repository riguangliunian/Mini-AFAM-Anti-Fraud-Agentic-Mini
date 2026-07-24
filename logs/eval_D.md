# Evaluation report — Full AFAM

**Total alerts**: 6
**Total wall-clock**: 70.7s (avg 11.7s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 66.7%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 100.0%  |
| Confidence calibrated (in expected range) | 66.7%   |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category          |   N | Strict   | Lenient   |   Rounds | Verdicts                |
|-------------------|-----|----------|-----------|----------|-------------------------|
| D_isolated_normal |   6 | 67%      | 100%      |        5 | escalate=2, not_fraud=4 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   1 | 100%         |
| [0.70,0.85)  |   3 | 100%         |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 6       |
| Avg recall on holdout     | 82.4%   |
| Avg FP-rate on holdout    | 0.11%   |
| Avg precision             | 96.6%   |
