# Evaluation report — few_shot (qwen3-4b-instruct_t0.3_t0.3)

**Total alerts**: 34
**Total wall-clock**: 2332.9s (avg 68.6s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 47.1%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 88.2%   |
| Confidence calibrated (in expected range) | 52.9%   |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts                                           |
|-----------------------|-----|----------|-----------|----------|----------------------------------------------------|
| A_obvious_gang        |   8 | 100%     | 100%      |        5 | fraud_confirmed=8                                  |
| B_subtle_immature     |   6 | 33%      | 83%       |        5 | fraud_unconfirmed=1, escalate=3, fraud_confirmed=2 |
| C_wifi_false_positive |   6 | 0%       | 83%       |        5 | escalate=5, fraud_uncertain=1                      |
| D_isolated_normal     |   6 | 0%       | 100%      |        5 | escalate=6                                         |
| E_novel_pattern       |   4 | 50%      | 50%       |        5 | escalate=2, fraud_unconfirmed=1, fraud_confirmed=1 |
| F_rule_robustness     |   4 | 100%     | 100%      |        5 | fraud_confirmed=4                                  |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   3 | 0%           |
| [0.70,0.85)  |   3 | 67%          |
| [0.85,1.00)  |  12 | 100%         |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 34      |
| Avg recall on holdout     | 75.6%   |
| Avg FP-rate on holdout    | 0.04%   |
| Avg precision             | 98.8%   |

## Wrong cases (need attention)

| Alert    | Category              | Expected        | Actual            |   Conf |   Rounds |
|----------|-----------------------|-----------------|-------------------|--------|----------|
| eval_B00 | B_subtle_immature     | fraud_confirmed | fraud_unconfirmed |   0.65 |        5 |
| eval_C01 | C_wifi_false_positive | not_fraud       | fraud_uncertain   |   0.65 |        5 |
| eval_E01 | E_novel_pattern       | escalate        | fraud_unconfirmed |   0.65 |        5 |
| eval_E03 | E_novel_pattern       | escalate        | fraud_confirmed   |   0.75 |        5 |