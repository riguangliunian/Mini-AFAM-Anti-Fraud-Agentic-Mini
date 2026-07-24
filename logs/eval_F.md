# Evaluation report — Full AFAM

**Total alerts**: 4
**Total wall-clock**: 51.4s (avg 12.6s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 50.0%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 100.0%  |
| Confidence calibrated (in expected range) | 50.0%   |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category          |   N | Strict   | Lenient   |   Rounds | Verdicts                      |
|-------------------|-----|----------|-----------|----------|-------------------------------|
| F_rule_robustness |   4 | 50%      | 100%      |        5 | fraud_confirmed=2, escalate=2 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   0 | —            |
| [0.70,0.85)  |   2 | 100%         |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 4       |
| Avg recall on holdout     | 76.5%   |
| Avg FP-rate on holdout    | 0.00%   |
| Avg precision             | 100.0%  |
