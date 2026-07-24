# Production Fraud Diagnosis Agent - baseline

## Summary

| Metric                           | Value   |
|----------------------------------|---------|
| Events                           | 2       |
| Root-cause accuracy              | 100.0%  |
| Repair strategy accuracy         | 0.0%    |
| Joint success                    | 0.0%    |
| Average rounds                   | 10.0    |
| Average tool cost                | 6.80    |
| Replay pass rate                 | n/a     |
| Full retraining recommendations  | 0       |
| Unnecessary full retraining rate | 0.0%    |
| Premature fix rate               | 0.0%    |
| Required tool recall             | 100.0%  |
| Forbidden tool trajectory rate   | 0.0%    |
| Process success                  | 100.0%  |
| Overall success incl. process    | 0.0%    |

## Per Event

| Alert        | Category        | Difficulty   | Expected cause     | Diagnosed cause    | Expected repair   | Repair       | Task   | Process   |   Rounds |   Cost |
|--------------|-----------------|--------------|--------------------|--------------------|-------------------|--------------|--------|-----------|----------|--------|
| diag_data_01 | A_DataIntegrity | easy         | data_quality_issue | data_quality_issue | feature_patch     | human_review | no     | yes       |       10 |    6.8 |
| diag_data_02 | A_DataIntegrity | medium       | data_quality_issue | data_quality_issue | feature_patch     | human_review | no     | yes       |       10 |    6.8 |

## Per Category

| Category        |   N | Task success   | Process success   | Overall   |   Avg cost | Root causes        |
|-----------------|-----|----------------|-------------------|-----------|------------|--------------------|
| A_DataIntegrity |   2 | 0.0%           | 100.0%            | 0.0%      |        6.8 | data_quality_issue |

## Per Root Cause

| Root cause         |   N | Joint success   |   Avg cost |
|--------------------|-----|-----------------|------------|
| data_quality_issue |   2 | 0.0%            |        6.8 |
