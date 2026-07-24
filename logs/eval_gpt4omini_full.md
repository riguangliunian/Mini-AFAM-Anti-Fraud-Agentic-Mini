# Evaluation report — Full AFAM

**Total alerts**: 34
**Total wall-clock**: 1174.5s (avg 34.5s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 76.5%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 88.2%   |
| Confidence calibrated (in expected range) | 55.9%   |
| Avg rounds                                | 4.9     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts                      |
|-----------------------|-----|----------|-----------|----------|-------------------------------|
| A_obvious_gang        |   8 | 88%      | 88%       |      5   | fraud_confirmed=7, escalate=1 |
| B_subtle_immature     |   6 | 83%      | 100%      |      4.5 | fraud_confirmed=5, escalate=1 |
| C_wifi_false_positive |   6 | 100%     | 100%      |      4.7 | not_fraud=6                   |
| D_isolated_normal     |   6 | 83%      | 100%      |      5   | escalate=1, not_fraud=5       |
| E_novel_pattern       |   4 | 25%      | 25%       |      5   | fraud_confirmed=3, escalate=1 |
| F_rule_robustness     |   4 | 50%      | 100%      |      5   | fraud_confirmed=2, escalate=2 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   7 | 86%          |
| [0.70,0.85)  |  21 | 90%          |
| [0.85,1.00)  |   0 | —            |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 32      |
| Avg recall on holdout     | 74.8%   |
| Avg FP-rate on holdout    | 0.04%   |
| Avg precision             | 98.8%   |

## Wrong cases (need attention)

| Alert    | Category        | Expected        | Actual          |   Conf |   Rounds |
|----------|-----------------|-----------------|-----------------|--------|----------|
| eval_A04 | A_obvious_gang  | fraud_confirmed | escalate        |    0   |        5 |
| eval_E00 | E_novel_pattern | escalate        | fraud_confirmed |    0.7 |        5 |
| eval_E01 | E_novel_pattern | escalate        | fraud_confirmed |    0.6 |        5 |
| eval_E03 | E_novel_pattern | escalate        | fraud_confirmed |    0.7 |        5 |