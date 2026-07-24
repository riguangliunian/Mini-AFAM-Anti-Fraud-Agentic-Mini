# Evaluation report — baseline (qwen3-4b-instruct)

**Total alerts**: 34
**Total wall-clock**: 1830.3s (avg 53.8s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 41.2%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 41.2%   |
| Confidence calibrated (in expected range) | 88.2%   |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts                                               |
|-----------------------|-----|----------|-----------|----------|--------------------------------------------------------|
| A_obvious_gang        |   8 | 100%     | 100%      |      5   | fraud_confirmed=8                                      |
| B_subtle_immature     |   6 | 33%      | 33%       |      5   | fraud_probable=4, fraud_confirmed=2                    |
| C_wifi_false_positive |   6 | 0%       | 0%        |      5   | fraud_confirmed=6                                      |
| D_isolated_normal     |   6 | 0%       | 0%        |      5   | fraud_confirmed=6                                      |
| E_novel_pattern       |   4 | 0%       | 0%        |      5.2 | fraud_probable=1, FRAUD_CONFIRMED=2, fraud_confirmed=1 |
| F_rule_robustness     |   4 | 100%     | 100%      |      5   | fraud_confirmed=4                                      |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   5 | 0%           |
| [0.70,0.85)  |   3 | 67%          |
| [0.85,1.00)  |  26 | 46%          |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 33      |
| Avg recall on holdout     | 75.0%   |
| Avg FP-rate on holdout    | 0.04%   |
| Avg precision             | 98.7%   |

## Wrong cases (need attention)

| Alert    | Category              | Expected        | Actual          |   Conf |   Rounds |
|----------|-----------------------|-----------------|-----------------|--------|----------|
| eval_B00 | B_subtle_immature     | fraud_confirmed | fraud_probable  |   0.65 |        5 |
| eval_B01 | B_subtle_immature     | fraud_confirmed | fraud_probable  |   0.65 |        5 |
| eval_B02 | B_subtle_immature     | fraud_confirmed | fraud_probable  |   0.65 |        5 |
| eval_B04 | B_subtle_immature     | fraud_confirmed | fraud_probable  |   0.65 |        5 |
| eval_C00 | C_wifi_false_positive | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_C01 | C_wifi_false_positive | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_C02 | C_wifi_false_positive | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_C03 | C_wifi_false_positive | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_C04 | C_wifi_false_positive | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_C05 | C_wifi_false_positive | not_fraud       | fraud_confirmed |   0.98 |        5 |
| eval_D00 | D_isolated_normal     | not_fraud       | fraud_confirmed |   0.98 |        5 |
| eval_D01 | D_isolated_normal     | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_D02 | D_isolated_normal     | not_fraud       | fraud_confirmed |   0.98 |        5 |
| eval_D03 | D_isolated_normal     | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_D04 | D_isolated_normal     | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_D05 | D_isolated_normal     | not_fraud       | fraud_confirmed |   0.95 |        5 |
| eval_E00 | E_novel_pattern       | escalate        | fraud_probable  |   0.65 |        5 |
| eval_E01 | E_novel_pattern       | escalate        | FRAUD_CONFIRMED |   0.92 |        5 |
| eval_E02 | E_novel_pattern       | escalate        | FRAUD_CONFIRMED |   0.95 |        5 |
| eval_E03 | E_novel_pattern       | escalate        | fraud_confirmed |   0.75 |        6 |