# Production Fraud Diagnosis & Optimization Agent

## Goal

This workflow simulates how a senior fraud algorithm engineer diagnoses a production model degradation alert. The agent does not train models directly. It chooses what to inspect next, collects structured evidence from tools, forms root-cause hypotheses, validates a candidate repair with replay, and stops with a bounded recommendation.

## Architecture

```text
Model monitoring alert
  -> DiagnosisState
  -> Planner
  -> ToolLab
       SQL profile
       Data quality
       PSI
       SHAP shift
       Behavior sequence shift
       Graph pattern shift
       Label maturity
       Replay backtest
  -> Evidence and hypotheses
  -> RuleStream validation
  -> Repair strategy
```

## Root Causes

- `data_quality_issue`
- `feature_distribution_drift`
- `label_delay`
- `traffic_segment_shift`
- `attack_pattern_drift`
- `rule_interaction_issue`
- `threshold_miscalibration`
- `model_capacity_issue`

## Evaluation Categories

The benchmark is grouped by production diagnosis category before root cause:

- `A_data_pipeline`: upstream SQL, join, missing-rate, and feature freshness issues
- `B_feature_drift`: feature distribution and attribution drift
- `C_label_feedback`: delayed or immature fraud labels
- `D_segment_calibration`: traffic mix shift and threshold miscalibration
- `E_attack_pattern`: behavior and graph pattern drift from new attacks
- `F_rule_policy_interaction`: rule/routing changes that alter scored traffic
- `G_model_capacity`: broad degradation where light patches are insufficient
- `H_confounded_mixed_signals`: conflicting evidence and misleading first-order signals

## Repair Strategies

- `feature_patch`
- `threshold_adjustment`
- `rule_update`
- `partial_retraining`
- `full_retraining`
- `defer_until_label_mature`
- `human_review`

## Files

```text
src/production_diagnosis/
  state.py          typed State/Action/Outcome/Trajectory
  policy.py         mock planner and LLM planner
  tool_lab.py       replaceable simulated tool layer
  rule_stream.py    hard guards
  memory.py         accepted trajectory memory and retrieval
  orchestrator.py   State + Planner + Tool + Evaluation loop
  main.py           CLI runner

data/production_diagnosis/
  eval_events.json
  seed_diagnosis_trajectories.json

experiments/
  evaluate_diagnosis.py
  build_diagnosis_dpo_data.py
```

## Run

```bash
LLM_MODEL=mock python -m src.production_diagnosis.main --event diag_attack_01

LLM_MODEL=mock python -m experiments.evaluate_diagnosis \
  --modes baseline retrieval \
  --output-prefix diagnosis_eval

LLM_MODEL=mock python -m experiments.evaluate_diagnosis \
  --modes baseline \
  --category E_attack_pattern

python -m experiments.build_diagnosis_dpo_data \
  --output logs/diagnosis_dpo_train.jsonl
```

The mock environment is deterministic and intended for workflow regression. Its 100% score is not a real model-performance claim. Real experiments should replace `SimulatedDiagnosisToolLab` with implementations connected to SQL, feature stores, PSI jobs, SHAP jobs, graph jobs, behavior sequence jobs, and replay services.

## DPO Target

The generated preference data is decision-level:

```text
same DiagnosisState
  chosen: inspect the next useful evidence source or select the validated repair
  rejected: premature full retraining, premature repair, or production change without replay
```

This trains the planner to learn when to inspect, when to stop, and which repair is justified, instead of learning model training itself.
