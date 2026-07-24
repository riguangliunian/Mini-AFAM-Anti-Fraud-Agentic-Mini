# Evaluation report — few_shot (qwen3-4b-instruct_t0.6_t0.6)

**Total alerts**: 34
**Total wall-clock**: 2516.3s (avg 74.0s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 35.3%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 70.6%   |
| Confidence calibrated (in expected range) | 52.9%   |
| Avg rounds                                | 4.9     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts                                                                  |
|-----------------------|-----|----------|-----------|----------|---------------------------------------------------------------------------|
| A_obvious_gang        |   8 | 88%      | 88%       |      4.9 | fraud_confirmed=7, escalate=1                                             |
| B_subtle_immature     |   6 | 17%      | 83%       |      5   | escalate=4, fraud_likelihood_high=1, fraud_confirmed=1                    |
| C_wifi_false_positive |   6 | 0%       | 17%       |      5   | fraud_uncertain=5, escalate=1                                             |
| D_isolated_normal     |   6 | 0%       | 100%      |      5   | escalate=6                                                                |
| E_novel_pattern       |   4 | 25%      | 25%       |      5   | escalate=1, fraud_potential=1, fraud_likelihood_high=1, fraud_confirmed=1 |
| F_rule_robustness     |   4 | 75%      | 100%      |      4.8 | fraud_confirmed=3, escalate=1                                             |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   8 | 0%           |
| [0.70,0.85)  |   2 | 50%          |
| [0.85,1.00)  |  10 | 100%         |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 34      |
| Avg recall on holdout     | 75.7%   |
| Avg FP-rate on holdout    | 0.04%   |
| Avg precision             | 98.8%   |

## Wrong cases (need attention)

| Alert    | Category              | Expected        | Actual                |   Conf |   Rounds |
|----------|-----------------------|-----------------|-----------------------|--------|----------|
| eval_A02 | A_obvious_gang        | fraud_confirmed | escalate              |   0    |        4 |
| eval_B02 | B_subtle_immature     | fraud_confirmed | fraud_likelihood_high |   0.65 |        5 |
| eval_C00 | C_wifi_false_positive | not_fraud       | fraud_uncertain       |   0.65 |        5 |
| eval_C01 | C_wifi_false_positive | not_fraud       | fraud_uncertain       |   0.65 |        5 |
| eval_C02 | C_wifi_false_positive | not_fraud       | fraud_uncertain       |   0.65 |        5 |
| eval_C03 | C_wifi_false_positive | not_fraud       | fraud_uncertain       |   0.65 |        5 |
| eval_C04 | C_wifi_false_positive | not_fraud       | fraud_uncertain       |   0.65 |        5 |
| eval_E01 | E_novel_pattern       | escalate        | fraud_potential       |   0.65 |        5 |
| eval_E02 | E_novel_pattern       | escalate        | fraud_likelihood_high |   0.65 |        5 |
| eval_E03 | E_novel_pattern       | escalate        | fraud_confirmed       |   0.75 |        5 |