# Aggregated evaluation — GPT-4o-mini (Full AFAM)

**Total alerts**: 34

## Overall

| Metric | Value |
|---|---|
| Strict accuracy | 67.6% |
| Lenient accuracy | 82.4% |
| Avg rounds (weighted) | 4.8 |
| Rules generated | 30 |
| Avg rule recall | 75.3% |
| Avg rule FP-rate | 0.04% |
| Avg rule precision | 98.9% |

## Per-category

| Category | N | Strict | Lenient | Rounds | Verdicts |
|---|---|---|---|---|---|
| A_obvious_gang | 8 | 75% | 75% | 5 | fraud_confirmed=6, escalate=2 |
| B_subtle_immature | 6 | 83% | 100% | 4.7 | fraud_confirmed=5, escalate=1 |
| C_wifi_false_positive | 6 | 100% | 100% | 4.3 | not_fraud=6 |
| D_isolated_normal | 6 | 67% | 100% | 5 | escalate=2, not_fraud=4 |
| E_novel_pattern | 4 | 0% | 0% | 5 | fraud_confirmed=4 |
| F_rule_robustness | 4 | 50% | 100% | 5 | fraud_confirmed=2, escalate=2 |

## Wrong cases (4)

| Alert | Category | Expected | Actual | Conf | Rounds |
|---|---|---|---|---|---|
| eval_A04 | A_obvious_gang | fraud_confirmed | escalate |      0 |        5 |
| eval_E00 | E_novel_pattern | escalate   | fraud_confirmed |    0.7 |        5 |
| eval_E01 | E_novel_pattern | escalate   | fraud_confirmed |    0.7 |        5 |
| eval_E02 | E_novel_pattern | escalate   | fraud_confirmed |    0.6 |        5 |

---

# Aggregated evaluation — Mock LLM (Full AFAM)

**Total alerts**: 34

## Overall

| Metric | Value |
|---|---|
| Strict accuracy | 58.9% |
| Lenient accuracy | 85.4% |
| Avg rounds (weighted) | 3.9 |
| Rules generated | 22 |
| Avg rule recall | 39.1% |
| Avg rule FP-rate | 0.00% |
| Avg rule precision | 100.0% |

## Per-category

| Category | N | Strict | Lenient | Rounds | Verdicts |
|---|---|---|---|---|---|
| A_obvious_gang | 8 | 88% | 88% | 4.6 | fraud_confirmed=7, escalate=1 |
| B_subtle_immature | 6 | 0% | 33% | 5 | not_fraud=4, escalate=2 |
| C_wifi_false_positive | 6 | 100% | 100% | 5 | not_fraud=6 |
| D_isolated_normal | 6 | 0% | 100% | 2 | escalate=6 |
| E_novel_pattern | 4 | 100% | 100% | 2 | escalate=4 |
| F_rule_robustness | 4 | 75% | 100% | 4.2 | fraud_confirmed=3, escalate=1 |

## Wrong cases (4)

| Alert | Category | Expected | Actual | Conf | Rounds |
|---|---|---|---|---|---|
| eval_A06 | A_obvious_gang    | fraud_confirmed | escalate  |    0   |        2 |
| eval_B00 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |
| eval_B01 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |
| eval_B03 | B_subtle_immature | fraud_confirmed | not_fraud |    0.7 |        5 |