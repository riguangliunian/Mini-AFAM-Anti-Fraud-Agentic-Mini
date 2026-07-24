# GNN Model Refresh Agent — baseline

## Summary

| Metric                       | Value   |
|------------------------------|---------|
| Events                       | 12      |
| Root-cause accuracy          | 100.0%  |
| End-to-end refresh success   | 100.0%  |
| Average rounds               | 7.3     |
| Average budget cost          | 7.20    |
| Unnecessary retrain rate     | 0.0%    |
| Tool failure trajectory rate | 0.0%    |

## Per event

| Event               | Expected         | Diagnosed        | Recommendation   | Success   |   Rounds |   Cost |
|---------------------|------------------|------------------|------------------|-----------|----------|--------|
| refresh_feature_01  | feature_drift    | feature_drift    | shadow_deploy    | yes       |        7 |    6.6 |
| refresh_feature_02  | feature_drift    | feature_drift    | shadow_deploy    | yes       |        7 |    6.6 |
| refresh_graph_01    | graph_drift      | graph_drift      | shadow_deploy    | yes       |        8 |    8.2 |
| refresh_graph_02    | graph_drift      | graph_drift      | shadow_deploy    | yes       |        8 |    8.2 |
| refresh_label_01    | label_delay      | label_delay      | shadow_deploy    | yes       |        7 |    6.5 |
| refresh_label_02    | label_delay      | label_delay      | shadow_deploy    | yes       |        7 |    6.5 |
| refresh_pipeline_01 | pipeline_failure | pipeline_failure | shadow_deploy    | yes       |        7 |    6.6 |
| refresh_pipeline_02 | pipeline_failure | pipeline_failure | shadow_deploy    | yes       |        7 |    6.6 |
| refresh_segment_01  | segment_shift    | segment_shift    | shadow_deploy    | yes       |        7 |    7.1 |
| refresh_segment_02  | segment_shift    | segment_shift    | shadow_deploy    | yes       |        7 |    7.1 |
| refresh_novel_01    | novel_attack     | novel_attack     | shadow_deploy    | yes       |        8 |    8.2 |
| refresh_novel_02    | novel_attack     | novel_attack     | shadow_deploy    | yes       |        8 |    8.2 |

## Per drift type

| Drift type       |   N | Refresh success   |
|------------------|-----|-------------------|
| feature_drift    |   2 | 100.0%            |
| graph_drift      |   2 | 100.0%            |
| label_delay      |   2 | 100.0%            |
| novel_attack     |   2 | 100.0%            |
| pipeline_failure |   2 | 100.0%            |
| segment_shift    |   2 | 100.0%            |
