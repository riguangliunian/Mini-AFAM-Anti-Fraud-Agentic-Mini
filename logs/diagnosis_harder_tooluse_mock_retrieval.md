# Production Fraud Diagnosis Agent - retrieval

## Summary

| Metric                           | Value   |
|----------------------------------|---------|
| Events                           | 40      |
| Root-cause accuracy              | 87.5%   |
| Repair strategy accuracy         | 87.5%   |
| Joint success                    | 87.5%   |
| Average rounds                   | 6.6     |
| Average tool cost                | 4.54    |
| Replay pass rate                 | 88.6%   |
| Full retraining recommendations  | 4       |
| Unnecessary full retraining rate | 0.0%    |
| Premature fix rate               | 0.0%    |
| Required tool recall             | 97.5%   |
| Forbidden tool trajectory rate   | 0.0%    |
| Process success                  | 95.0%   |
| Overall success incl. process    | 85.0%   |

## Per Event

| Alert                               | Category            | Difficulty      | Expected cause             | Diagnosed cause            | Expected repair          | Repair                   | Task   | Process   |   Rounds |   Cost |
|-------------------------------------|---------------------|-----------------|----------------------------|----------------------------|--------------------------|--------------------------|--------|-----------|----------|--------|
| diag_data_01                        | A_DataIntegrity     | easy            | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch            | yes    | yes       |        8 |    5.3 |
| diag_data_02                        | A_DataIntegrity     | medium          | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch            | yes    | yes       |        8 |    5.3 |
| diag_feature_01                     | B_DistributionShift | medium          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining       | yes    | yes       |        6 |    4.2 |
| diag_feature_02                     | B_DistributionShift | medium          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining       | yes    | yes       |        6 |    4.2 |
| diag_label_01                       | D_FeedbackLoop      | easy            | label_delay                | label_delay                | defer_until_label_mature | defer_until_label_mature | yes    | yes       |        5 |    2.5 |
| diag_label_02                       | D_FeedbackLoop      | medium          | label_delay                | label_delay                | defer_until_label_mature | defer_until_label_mature | yes    | yes       |        5 |    2.5 |
| diag_segment_01                     | B_DistributionShift | medium          | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_segment_02                     | B_DistributionShift | hard            | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_attack_01                      | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_attack_02                      | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_rule_01                        | D_FeedbackLoop      | medium          | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_rule_02                        | D_FeedbackLoop      | medium          | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_threshold_01                   | B_DistributionShift | medium          | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_threshold_02                   | B_DistributionShift | medium          | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_capacity_01                    | B_DistributionShift | hard            | model_capacity_issue       | model_capacity_issue       | full_retraining          | full_retraining          | yes    | yes       |        6 |    4.6 |
| diag_capacity_02                    | B_DistributionShift | hard            | model_capacity_issue       | model_capacity_issue       | full_retraining          | full_retraining          | yes    | yes       |        6 |    4.6 |
| diag_confound_01                    | A_DataIntegrity     | confounded      | data_quality_issue         | feature_distribution_drift | feature_patch            | human_review             | no     | yes       |        7 |    5.5 |
| diag_confound_02                    | D_FeedbackLoop      | confounded      | rule_interaction_issue     | threshold_miscalibration   | rule_update              | human_review             | no     | yes       |        6 |    4.4 |
| diag_confound_03                    | C_AdversarialDrift  | confounded      | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_confound_04                    | B_DistributionShift | confounded      | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_integrity_skew_01              | A_DataIntegrity     | hard            | data_quality_issue         | feature_distribution_drift | feature_patch            | human_review             | no     | yes       |        5 |    4.2 |
| diag_integrity_delay_01             | A_DataIntegrity     | medium          | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch            | yes    | yes       |        8 |    5.3 |
| diag_dist_population_01             | B_DistributionShift | medium          | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_dist_capacity_03               | B_DistributionShift | hard            | model_capacity_issue       | model_capacity_issue       | full_retraining          | full_retraining          | yes    | yes       |        6 |    4.6 |
| diag_dist_feature_03                | B_DistributionShift | medium          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining       | yes    | yes       |        6 |    4.2 |
| diag_adv_entity_01                  | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_adv_amount_split_01            | C_AdversarialDrift  | medium          | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_adv_proxy_01                   | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_feedback_review_01             | D_FeedbackLoop      | hard            | label_delay                | label_delay                | defer_until_label_mature | defer_until_label_mature | yes    | yes       |        5 |    2.5 |
| diag_feedback_rule_loop_01          | D_FeedbackLoop      | hard            | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_feedback_capacity_attack_01    | D_FeedbackLoop      | confounded      | rule_interaction_issue     | label_delay                | rule_update              | defer_until_label_mature | no     | yes       |        5 |    2.5 |
| diag_integrity_entity_resolution_01 | A_DataIntegrity     | hard            | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch            | yes    | yes       |        8 |    5.3 |
| diag_tool_required_sql_01           | E_AgentToolUse      | tool_order      | data_quality_issue         | feature_distribution_drift | feature_patch            | human_review             | no     | no        |        5 |    4.2 |
| diag_tool_label_guard_01            | E_AgentToolUse      | tool_guard      | label_delay                | label_delay                | defer_until_label_mature | defer_until_label_mature | yes    | yes       |        5 |    2.5 |
| diag_tool_replay_required_01        | E_AgentToolUse      | tool_validation | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_tool_minimal_repair_01         | E_AgentToolUse      | minimal_repair  | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment     | yes    | yes       |        6 |    3.8 |
| diag_tool_attack_followup_01        | E_AgentToolUse      | tool_followup   | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update              | yes    | yes       |        8 |    5.8 |
| diag_tool_no_redundant_heavy_01     | E_AgentToolUse      | budget          | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update              | yes    | no        |        8 |    5.8 |
| diag_tool_escalate_unknown_01       | E_AgentToolUse      | unknown         | model_capacity_issue       | model_capacity_issue       | full_retraining          | full_retraining          | yes    | yes       |        6 |    4.6 |
| diag_tool_cost_cap_01               | E_AgentToolUse      | budget          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining       | yes    | yes       |        6 |    4.2 |

## Per Category

| Category            |   N | Task success   | Process success   | Overall   |   Avg cost | Root causes                                                                                                                                                                      |
|---------------------|-----|----------------|-------------------|-----------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A_DataIntegrity     |   6 | 66.7%          | 100.0%            | 66.7%     |       5.15 | data_quality_issue                                                                                                                                                               |
| B_DistributionShift |  12 | 100.0%         | 100.0%            | 100.0%    |       4.1  | feature_distribution_drift, model_capacity_issue, threshold_miscalibration, traffic_segment_shift                                                                                |
| C_AdversarialDrift  |   6 | 100.0%         | 100.0%            | 100.0%    |       5.8  | attack_pattern_drift                                                                                                                                                             |
| D_FeedbackLoop      |   8 | 75.0%          | 100.0%            | 75.0%     |       3.98 | label_delay, rule_interaction_issue                                                                                                                                              |
| E_AgentToolUse      |   8 | 87.5%          | 75.0%             | 75.0%     |       4.34 | attack_pattern_drift, data_quality_issue, feature_distribution_drift, label_delay, model_capacity_issue, rule_interaction_issue, threshold_miscalibration, traffic_segment_shift |

## Per Root Cause

| Root cause                 |   N | Joint success   |   Avg cost |
|----------------------------|-----|-----------------|------------|
| attack_pattern_drift       |   7 | 100.0%          |       5.8  |
| data_quality_issue         |   7 | 57.1%           |       5.01 |
| feature_distribution_drift |   4 | 100.0%          |       4.2  |
| label_delay                |   4 | 100.0%          |       2.5  |
| model_capacity_issue       |   4 | 100.0%          |       4.6  |
| rule_interaction_issue     |   6 | 66.7%           |       5.02 |
| threshold_miscalibration   |   3 | 100.0%          |       3.8  |
| traffic_segment_shift      |   5 | 100.0%          |       3.8  |
