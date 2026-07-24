# Production Fraud Diagnosis Agent - baseline
Category filter: `E_attack_pattern`


## Summary

| Metric                           | Value   |
|----------------------------------|---------|
| Events                           | 2       |
| Root-cause accuracy              | 100.0%  |
| Repair strategy accuracy         | 100.0%  |
| Joint success                    | 100.0%  |
| Average rounds                   | 6.0     |
| Average tool cost                | 4.30    |
| Replay pass rate                 | 100.0%  |
| Full retraining recommendations  | 0       |
| Unnecessary full retraining rate | 0.0%    |
| Premature fix rate               | 0.0%    |

## Per Event

| Alert          | Category         | Difficulty   | Expected cause       | Diagnosed cause      | Expected repair   | Repair      | Success   |   Rounds |   Cost |
|----------------|------------------|--------------|----------------------|----------------------|-------------------|-------------|-----------|----------|--------|
| diag_attack_01 | E_attack_pattern | hard         | attack_pattern_drift | attack_pattern_drift | rule_update       | rule_update | yes       |        6 |    4.3 |
| diag_attack_02 | E_attack_pattern | hard         | attack_pattern_drift | attack_pattern_drift | rule_update       | rule_update | yes       |        6 |    4.3 |

## Per Category

| Category         |   N | Joint success   |   Avg cost | Root causes          |
|------------------|-----|-----------------|------------|----------------------|
| E_attack_pattern |   2 | 100.0%          |        4.3 | attack_pattern_drift |

## Per Root Cause

| Root cause           |   N | Joint success   |   Avg cost |
|----------------------|-----|-----------------|------------|
| attack_pattern_drift |   2 | 100.0%          |        4.3 |
