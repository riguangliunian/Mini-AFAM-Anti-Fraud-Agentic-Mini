# Production Fraud Diagnosis Agent - retrieval

## Summary

| Metric                           | Value   |
|----------------------------------|---------|
| Events                           | 20      |
| Root-cause accuracy              | 85.0%   |
| Repair strategy accuracy         | 85.0%   |
| Joint success                    | 85.0%   |
| Average rounds                   | 6.3     |
| Average tool cost                | 4.29    |
| Replay pass rate                 | 88.2%   |
| Full retraining recommendations  | 2       |
| Unnecessary full retraining rate | 0.0%    |
| Premature fix rate               | 0.0%    |

## Per Event

| Alert             | Category                   | Difficulty   | Expected cause             | Diagnosed cause            | Expected repair          | Repair                   | Success   |   Rounds |   Cost |
|-------------------|----------------------------|--------------|----------------------------|----------------------------|--------------------------|--------------------------|-----------|----------|--------|
| diag_data_01      | A_data_pipeline            | easy         | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch            | yes       |        8 |    5.3 |
| diag_data_02      | A_data_pipeline            | medium       | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch            | yes       |        8 |    5.3 |
| diag_feature_01   | B_feature_drift            | medium       | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining       | yes       |        6 |    4.2 |
| diag_feature_02   | B_feature_drift            | medium       | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining       | yes       |        6 |    4.2 |
| diag_label_01     | C_label_feedback           | easy         | label_delay                | label_delay                | defer_until_label_mature | defer_until_label_mature | yes       |        5 |    2.5 |
| diag_label_02     | C_label_feedback           | medium       | label_delay                | label_delay                | defer_until_label_mature | defer_until_label_mature | yes       |        5 |    2.5 |
| diag_segment_01   | D_segment_calibration      | medium       | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes       |        6 |    3.8 |
| diag_segment_02   | D_segment_calibration      | hard         | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes       |        6 |    3.8 |
| diag_attack_01    | E_attack_pattern           | hard         | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes       |        8 |    5.8 |
| diag_attack_02    | E_attack_pattern           | hard         | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes       |        8 |    5.8 |
| diag_rule_01      | F_rule_policy_interaction  | medium       | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update              | yes       |        8 |    5.8 |
| diag_rule_02      | F_rule_policy_interaction  | medium       | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update              | yes       |        8 |    5.8 |
| diag_threshold_01 | D_segment_calibration      | medium       | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment     | yes       |        6 |    3.8 |
| diag_threshold_02 | D_segment_calibration      | medium       | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment     | yes       |        6 |    3.8 |
| diag_capacity_01  | G_model_capacity           | hard         | model_capacity_issue       | model_capacity_issue       | full_retraining          | full_retraining          | yes       |        6 |    4.6 |
| diag_capacity_02  | G_model_capacity           | hard         | model_capacity_issue       | model_capacity_issue       | full_retraining          | full_retraining          | yes       |        6 |    4.6 |
| diag_confound_01  | H_confounded_mixed_signals | hard         | data_quality_issue         | feature_distribution_drift | feature_patch            | human_review             | no        |        5 |    4.2 |
| diag_confound_02  | H_confounded_mixed_signals | hard         | rule_interaction_issue     | threshold_miscalibration   | rule_update              | human_review             | no        |        5 |    3.8 |
| diag_confound_03  | H_confounded_mixed_signals | hard         | attack_pattern_drift       | label_delay                | rule_update              | defer_until_label_mature | no        |        5 |    2.5 |
| diag_confound_04  | H_confounded_mixed_signals | hard         | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes       |        6 |    3.8 |

## Per Category

| Category                   |   N | Joint success   |   Avg cost | Root causes                                                                             |
|----------------------------|-----|-----------------|------------|-----------------------------------------------------------------------------------------|
| A_data_pipeline            |   2 | 100.0%          |       5.3  | data_quality_issue                                                                      |
| B_feature_drift            |   2 | 100.0%          |       4.2  | feature_distribution_drift                                                              |
| C_label_feedback           |   2 | 100.0%          |       2.5  | label_delay                                                                             |
| D_segment_calibration      |   4 | 100.0%          |       3.8  | threshold_miscalibration, traffic_segment_shift                                         |
| E_attack_pattern           |   2 | 100.0%          |       5.8  | attack_pattern_drift                                                                    |
| F_rule_policy_interaction  |   2 | 100.0%          |       5.8  | rule_interaction_issue                                                                  |
| G_model_capacity           |   2 | 100.0%          |       4.6  | model_capacity_issue                                                                    |
| H_confounded_mixed_signals |   4 | 25.0%           |       3.58 | attack_pattern_drift, data_quality_issue, rule_interaction_issue, traffic_segment_shift |

## Per Root Cause

| Root cause                 |   N | Joint success   |   Avg cost |
|----------------------------|-----|-----------------|------------|
| attack_pattern_drift       |   3 | 66.7%           |       4.7  |
| data_quality_issue         |   3 | 66.7%           |       4.93 |
| feature_distribution_drift |   2 | 100.0%          |       4.2  |
| label_delay                |   2 | 100.0%          |       2.5  |
| model_capacity_issue       |   2 | 100.0%          |       4.6  |
| rule_interaction_issue     |   3 | 66.7%           |       5.13 |
| threshold_miscalibration   |   2 | 100.0%          |       3.8  |
| traffic_segment_shift      |   3 | 100.0%          |       3.8  |
