# Evaluation report — Full AFAM

**Total alerts**: 34
**Total wall-clock**: 0.6s (avg 0.0s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 58.8%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 85.3%   |
| Confidence calibrated (in expected range) | 70.6%   |
| Avg rounds                                | 3.9     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts                      |
|-----------------------|-----|----------|-----------|----------|-------------------------------|
| A_obvious_gang        |   8 | 88%      | 88%       |      4.6 | fraud_confirmed=7, escalate=1 |
| B_subtle_immature     |   6 | 0%       | 33%       |      5   | not_fraud=4, escalate=2       |
| C_wifi_false_positive |   6 | 100%     | 100%      |      5   | not_fraud=6                   |
| D_isolated_normal     |   6 | 0%       | 100%      |      2   | escalate=6                    |
| E_novel_pattern       |   4 | 100%     | 100%      |      2   | escalate=4                    |
| F_rule_robustness     |   4 | 75%      | 100%      |      4.2 | fraud_confirmed=3, escalate=1 |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   0 | —            |
| [0.70,0.85)  |  10 | 60%          |
| [0.85,1.00)  |  10 | 100%         |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 22      |
| Avg recall on holdout     | 39.1%   |
| Avg FP-rate on holdout    | 0.00%   |
| Avg precision             | 100.0%  |

## Wrong cases (need attention)

| Alert    | Category          | Expected        | Actual    |   Conf |   Rounds |
|----------|-------------------|-----------------|-----------|--------|----------|
| eval_A06 | A_obvious_gang    | fraud_confirmed | escalate  |    0   |        2 |
| eval_B00 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |
| eval_B01 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |
| eval_B03 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |
| eval_B05 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |