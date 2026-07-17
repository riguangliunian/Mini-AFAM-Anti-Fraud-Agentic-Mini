# Evaluation report — Full AFAM

**Total alerts**: 4
**Total wall-clock**: 53.9s (avg 13.3s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 0.0%    |
| Lenient accuracy (incl. alt_ok_verdicts)  | 0.0%    |
| Confidence calibrated (in expected range) | 0.0%    |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category        |   N | Strict   | Lenient   |   Rounds | Verdicts          |
|-----------------|-----|----------|-----------|----------|-------------------|
| E_novel_pattern |   4 | 0%       | 0%        |        5 | fraud_confirmed=4 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   2 | 0%           |
| [0.70,0.85)  |   2 | 0%           |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 4       |
| Avg recall on holdout     | 76.5%   |
| Avg FP-rate on holdout    | 0.00%   |
| Avg precision             | 100.0%  |

## Wrong cases (need attention)

| Alert    | Category        | Expected   | Actual          |   Conf |   Rounds |
|----------|-----------------|------------|-----------------|--------|----------|
| eval_E00 | E_novel_pattern | escalate   | fraud_confirmed |    0.7 |        5 |
| eval_E01 | E_novel_pattern | escalate   | fraud_confirmed |    0.7 |        5 |
| eval_E02 | E_novel_pattern | escalate   | fraud_confirmed |    0.6 |        5 |
| eval_E03 | E_novel_pattern | escalate   | fraud_confirmed |    0.6 |        5 |