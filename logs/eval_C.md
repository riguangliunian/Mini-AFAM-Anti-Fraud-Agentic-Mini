# Evaluation report — Full AFAM

**Total alerts**: 6
**Total wall-clock**: 68.1s (avg 11.2s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 100.0%  |
| Lenient accuracy (incl. alt_ok_verdicts)  | 100.0%  |
| Confidence calibrated (in expected range) | 100.0%  |
| Avg rounds                                | 4.3     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts    |
|-----------------------|-----|----------|-----------|----------|-------------|
| C_wifi_false_positive |   6 | 100%     | 100%      |      4.3 | not_fraud=6 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   3 | 100%         |
| [0.70,0.85)  |   3 | 100%         |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 4       |
| Avg recall on holdout     | 82.4%   |
| Avg FP-rate on holdout    | 0.11%   |
| Avg precision             | 96.6%   |
