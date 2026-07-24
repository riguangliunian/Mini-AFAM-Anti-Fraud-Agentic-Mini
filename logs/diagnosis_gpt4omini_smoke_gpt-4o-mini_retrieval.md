# Production Fraud Diagnosis Agent - retrieval

## Summary

| Metric                           | Value   |
|----------------------------------|---------|
| Events                           | 2       |
| Root-cause accuracy              | 100.0%  |
| Repair strategy accuracy         | 100.0%  |
| Joint success                    | 100.0%  |
| Average rounds                   | 10.0    |
| Average tool cost                | 8.05    |
| Replay pass rate                 | 100.0%  |
| Full retraining recommendations  | 0       |
| Unnecessary full retraining rate | 0.0%    |
| Premature fix rate               | 50.0%   |
| Required tool recall             | 100.0%  |
| Forbidden tool trajectory rate   | 0.0%    |
| Process success                  | 100.0%  |
| Overall success incl. process    | 100.0%  |

## Per Event

| Alert        | Category        | Difficulty   | Expected cause     | Diagnosed cause    | Expected repair   | Repair        | Task   | Process   |   Rounds |   Cost |
|--------------|-----------------|--------------|--------------------|--------------------|-------------------|---------------|--------|-----------|----------|--------|
| diag_data_01 | A_DataIntegrity | easy         | data_quality_issue | data_quality_issue | feature_patch     | feature_patch | yes    | yes       |       10 |    8.3 |
| diag_data_02 | A_DataIntegrity | medium       | data_quality_issue | data_quality_issue | feature_patch     | feature_patch | yes    | yes       |       10 |    7.8 |

## Per Category

| Category        |   N | Task success   | Process success   | Overall   |   Avg cost | Root causes        |
|-----------------|-----|----------------|-------------------|-----------|------------|--------------------|
| A_DataIntegrity |   2 | 100.0%         | 100.0%            | 100.0%    |       8.05 | data_quality_issue |

## Per Root Cause

| Root cause         |   N | Joint success   |   Avg cost |
|--------------------|-----|-----------------|------------|
| data_quality_issue |   2 | 100.0%          |       8.05 |
