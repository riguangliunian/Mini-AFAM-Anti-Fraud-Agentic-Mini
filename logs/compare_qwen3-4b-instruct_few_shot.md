# Evaluation report — few_shot (qwen3-4b-instruct)

**Total alerts**: 34
**Total wall-clock**: 2170.9s (avg 63.8s per alert)

## Overall metrics

| Metric                                    | Value   |
|-------------------------------------------|---------|
| Strict accuracy (verdict exact match)     | 47.1%   |
| Lenient accuracy (incl. alt_ok_verdicts)  | 91.2%   |
| Confidence calibrated (in expected range) | 47.1%   |
| Avg rounds                                | 5.0     |

## Per-category breakdown

| Category              |   N | Strict   | Lenient   |   Rounds | Verdicts                                                                |
|-----------------------|-----|----------|-----------|----------|-------------------------------------------------------------------------|
| A_obvious_gang        |   8 | 100%     | 100%      |        5 | fraud_confirmed=8                                                       |
| B_subtle_immature     |   6 | 33%      | 100%      |        5 | escalate=4, fraud_confirmed=2                                           |
| C_wifi_false_positive |   6 | 17%      | 100%      |        5 | escalate=5, not_fraud=1                                                 |
| D_isolated_normal     |   6 | 0%       | 100%      |        5 | escalate=6                                                              |
| E_novel_pattern       |   4 | 25%      | 25%       |        5 | escalate=1, fraud_pending=1, fraud_likelihood_high=1, fraud_confirmed=1 |
| F_rule_robustness     |   4 | 100%     | 100%      |        5 | fraud_confirmed=4                                                       |

## Confidence calibration
(Only for cases where Agent produced a non-escalate verdict)

| Conf range   |   N | Strict acc   |
|--------------|-----|--------------|
| [0.00,0.50)  |   0 | —            |
| [0.50,0.70)  |   2 | 0%           |
| [0.70,0.85)  |   3 | 67%          |
| [0.85,1.00)  |  13 | 100%         |

## Generated rule quality

| Metric                    | Value   |
|---------------------------|---------|
| Number of rules generated | 34      |
| Avg recall on holdout     | 75.7%   |
| Avg FP-rate on holdout    | 0.04%   |
| Avg precision             | 98.8%   |

## Wrong cases (need attention)

| Alert    | Category        | Expected   | Actual                |   Conf |   Rounds |
|----------|-----------------|------------|-----------------------|--------|----------|
| eval_E01 | E_novel_pattern | escalate   | fraud_pending         |   0.65 |        5 |
| eval_E02 | E_novel_pattern | escalate   | fraud_likelihood_high |   0.65 |        5 |
| eval_E03 | E_novel_pattern | escalate   | fraud_confirmed       |   0.75 |        5 |