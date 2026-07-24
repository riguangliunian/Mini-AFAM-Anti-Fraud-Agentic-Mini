# Production Fraud Diagnosis Agent - retrieval

## Summary

| Metric                           | Value   |
|----------------------------------|---------|
| Events                           | 40      |
| Root-cause accuracy              | 90.0%   |
| Repair strategy accuracy         | 62.5%   |
| Joint success                    | 62.5%   |
| Average rounds                   | 7.8     |
| Average tool cost                | 5.27    |
| Replay pass rate                 | 66.7%   |
| Full retraining recommendations  | 0       |
| Unnecessary full retraining rate | 0.0%    |
| Premature fix rate               | 57.5%   |
| Required tool recall             | 87.5%   |
| Forbidden tool trajectory rate   | 0.0%    |
| Process success                  | 80.0%   |
| Overall success incl. process    | 50.0%   |

## Business Refresh Metrics

| Business metric          | Value   |
|--------------------------|---------|
| Expected metric recovery | 55.5%   |
| Recall recovery          | 49.9%   |
| Stability violation rate | 2.5%    |
| Average coverage loss    | 0.7%    |
| False-positive impact    | 0.11%   |
| Review workload change   | +1.7%   |
| Repair acceptance rate   | 62.5%   |
| Human handover rate      | 35.0%   |

## Fraud-Specific Production Metrics

| Fraud metric                        | Value   |
|-------------------------------------|---------|
| Fraud recall recovery               | 55.5%   |
| Amount recall recovery              | 49.5%   |
| Segment-level recovery              | 55.5%   |
| Novel attack detection rate         | 85.7%   |
| Label maturity guard accuracy       | 100.0%  |
| Rule robustness / bypass resistance | 46.2%   |
| Safe deployment rate                | 50.0%   |
| Avg time-to-mitigation              | 13.1h   |

## Per Event

| Alert                               | Category            | Difficulty      | Expected cause             | Diagnosed cause            | Expected repair          | Repair               | Task   | Process   | Metric recovery   | Accepted   | Safe deploy   |   Rounds |   Cost |
|-------------------------------------|---------------------|-----------------|----------------------------|----------------------------|--------------------------|----------------------|--------|-----------|-------------------|------------|---------------|----------|--------|
| diag_data_01                        | A_DataIntegrity     | easy            | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | yes       | 94.4%             | yes        | yes           |        8 |    6.3 |
| diag_data_02                        | A_DataIntegrity     | medium          | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | yes       | 87.5%             | yes        | yes           |        8 |    6.2 |
| diag_feature_01                     | B_DistributionShift | medium          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    5.4 |
| diag_feature_02                     | B_DistributionShift | medium          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4.8 |
| diag_label_01                       | D_FeedbackLoop      | easy            | label_delay                | label_delay                | defer_until_label_mature | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4   |
| diag_label_02                       | D_FeedbackLoop      | medium          | label_delay                | label_delay                | defer_until_label_mature | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4   |
| diag_segment_01                     | B_DistributionShift | medium          | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment | yes    | yes       | 87.5%             | yes        | yes           |        8 |    4.7 |
| diag_segment_02                     | B_DistributionShift | hard            | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment | yes    | yes       | 100.0%            | yes        | yes           |        8 |    4.7 |
| diag_attack_01                      | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update          | yes    | yes       | 84.2%             | yes        | yes           |        8 |    6.1 |
| diag_attack_02                      | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update          | yes    | yes       | 85.7%             | yes        | yes           |        8 |    5.9 |
| diag_rule_01                        | D_FeedbackLoop      | medium          | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update          | yes    | yes       | 90.9%             | yes        | yes           |        8 |    6.5 |
| diag_rule_02                        | D_FeedbackLoop      | medium          | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update          | yes    | yes       | 90.0%             | yes        | yes           |        8 |    6.5 |
| diag_threshold_01                   | B_DistributionShift | medium          | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment | yes    | yes       | 88.9%             | yes        | yes           |        8 |    5   |
| diag_threshold_02                   | B_DistributionShift | medium          | threshold_miscalibration   | threshold_miscalibration   | threshold_adjustment     | threshold_adjustment | yes    | yes       | 93.8%             | yes        | yes           |        8 |    5   |
| diag_capacity_01                    | B_DistributionShift | hard            | model_capacity_issue       | model_capacity_issue       | full_retraining          | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    6   |
| diag_capacity_02                    | B_DistributionShift | hard            | model_capacity_issue       | model_capacity_issue       | full_retraining          | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4.4 |
| diag_confound_01                    | A_DataIntegrity     | confounded      | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | yes       | 77.8%             | yes        | yes           |        8 |    6.3 |
| diag_confound_02                    | D_FeedbackLoop      | confounded      | rule_interaction_issue     | threshold_miscalibration   | rule_update              | threshold_adjustment | no     | yes       | 4.2%              | no         | no            |        8 |    5.1 |
| diag_confound_03                    | C_AdversarialDrift  | confounded      | attack_pattern_drift       | label_delay                | rule_update              | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4   |
| diag_confound_04                    | B_DistributionShift | confounded      | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment | yes    | yes       | 100.0%            | yes        | yes           |        8 |    4.7 |
| diag_integrity_skew_01              | A_DataIntegrity     | hard            | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | yes       | 85.7%             | yes        | yes           |        8 |    6.3 |
| diag_integrity_delay_01             | A_DataIntegrity     | medium          | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | yes       | 84.6%             | yes        | yes           |        8 |    6.3 |
| diag_dist_population_01             | B_DistributionShift | medium          | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment | yes    | yes       | 100.0%            | yes        | yes           |        8 |    4.7 |
| diag_dist_capacity_03               | B_DistributionShift | hard            | model_capacity_issue       | model_capacity_issue       | full_retraining          | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    5.8 |
| diag_dist_feature_03                | B_DistributionShift | medium          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    5   |
| diag_adv_entity_01                  | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update          | yes    | yes       | 83.3%             | yes        | yes           |        8 |    6.1 |
| diag_adv_amount_split_01            | C_AdversarialDrift  | medium          | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update          | yes    | yes       | 85.7%             | yes        | yes           |        8 |    6.1 |
| diag_adv_proxy_01                   | C_AdversarialDrift  | hard            | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update          | yes    | yes       | 86.7%             | yes        | yes           |        8 |    6.1 |
| diag_feedback_review_01             | D_FeedbackLoop      | hard            | label_delay                | label_delay                | defer_until_label_mature | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4   |
| diag_feedback_rule_loop_01          | D_FeedbackLoop      | hard            | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update          | yes    | yes       | 83.3%             | yes        | yes           |        8 |    6.1 |
| diag_feedback_capacity_attack_01    | D_FeedbackLoop      | confounded      | rule_interaction_issue     | label_delay                | rule_update              | human_review         | no     | yes       | 0.0%              | no         | no            |        8 |    4   |
| diag_integrity_entity_resolution_01 | A_DataIntegrity     | hard            | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | yes       | 86.7%             | yes        | yes           |        8 |    6.3 |
| diag_tool_required_sql_01           | E_AgentToolUse      | tool_order      | data_quality_issue         | data_quality_issue         | feature_patch            | feature_patch        | yes    | no        | 84.6%             | yes        | no            |        8 |    6.1 |
| diag_tool_label_guard_01            | E_AgentToolUse      | tool_guard      | label_delay                | label_delay                | defer_until_label_mature | human_review         | no     | no        | 0.0%              | no         | no            |        8 |    4   |
| diag_tool_replay_required_01        | E_AgentToolUse      | tool_validation | threshold_miscalibration   | unknown                    | threshold_adjustment     | human_review         | no     | no        | 0.0%              | no         | no            |        0 |    0   |
| diag_tool_minimal_repair_01         | E_AgentToolUse      | minimal_repair  | traffic_segment_shift      | traffic_segment_shift      | threshold_adjustment     | threshold_adjustment | yes    | no        | 100.0%            | yes        | no            |        8 |    4.7 |
| diag_tool_attack_followup_01        | E_AgentToolUse      | tool_followup   | attack_pattern_drift       | attack_pattern_drift       | rule_update              | rule_update          | yes    | no        | 81.2%             | yes        | no            |        8 |    6.1 |
| diag_tool_no_redundant_heavy_01     | E_AgentToolUse      | budget          | rule_interaction_issue     | rule_interaction_issue     | rule_update              | rule_update          | yes    | no        | 81.8%             | yes        | no            |        8 |    6.1 |
| diag_tool_escalate_unknown_01       | E_AgentToolUse      | unknown         | model_capacity_issue       | model_capacity_issue       | full_retraining          | human_review         | no     | no        | 0.0%              | no         | no            |        8 |    4.3 |
| diag_tool_cost_cap_01               | E_AgentToolUse      | budget          | feature_distribution_drift | feature_distribution_drift | partial_retraining       | partial_retraining   | yes    | no        | 90.9%             | yes        | no            |        8 |    7.2 |

## Per Category

| Category            |   N | Task success   | Process success   | Overall   | Metric recovery   | Acceptance   | Stability violation   | Fraud recall   | Safe deploy   |   Avg cost | Root causes                                                                                                                                                                      |
|---------------------|-----|----------------|-------------------|-----------|-------------------|--------------|-----------------------|----------------|---------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A_DataIntegrity     |   6 | 100.0%         | 100.0%            | 100.0%    | 86.1%             | 100.0%       | 0.0%                  | 86.1%          | 100.0%        |       6.28 | data_quality_issue                                                                                                                                                               |
| B_DistributionShift |  12 | 50.0%          | 100.0%            | 50.0%     | 47.5%             | 50.0%        | 0.0%                  | 47.5%          | 50.0%         |       5.02 | feature_distribution_drift, model_capacity_issue, threshold_miscalibration, traffic_segment_shift                                                                                |
| C_AdversarialDrift  |   6 | 83.3%          | 100.0%            | 83.3%     | 70.9%             | 83.3%        | 0.0%                  | 70.9%          | 83.3%         |       5.72 | attack_pattern_drift                                                                                                                                                             |
| D_FeedbackLoop      |   8 | 37.5%          | 100.0%            | 37.5%     | 33.6%             | 37.5%        | 12.5%                 | 33.6%          | 37.5%         |       5.03 | label_delay, rule_interaction_issue                                                                                                                                              |
| E_AgentToolUse      |   8 | 62.5%          | 0.0%              | 0.0%      | 54.8%             | 62.5%        | 0.0%                  | 54.8%          | 0.0%          |       4.81 | attack_pattern_drift, data_quality_issue, feature_distribution_drift, label_delay, model_capacity_issue, rule_interaction_issue, threshold_miscalibration, traffic_segment_shift |

## Per Root Cause

| Root cause                 |   N | Joint success   |   Avg cost |
|----------------------------|-----|-----------------|------------|
| attack_pattern_drift       |   7 | 85.7%           |       5.77 |
| data_quality_issue         |   7 | 100.0%          |       6.26 |
| feature_distribution_drift |   4 | 25.0%           |       5.6  |
| label_delay                |   4 | 0.0%            |       4    |
| model_capacity_issue       |   4 | 0.0%            |       5.12 |
| rule_interaction_issue     |   6 | 66.7%           |       5.72 |
| threshold_miscalibration   |   3 | 66.7%           |       3.33 |
| traffic_segment_shift      |   5 | 100.0%          |       4.7  |
