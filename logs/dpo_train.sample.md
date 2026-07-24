# DPO Training Pairs — Samples

## Pair 1 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_B00",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 0%, paste used: 100%\n- Avg label maturity: 0.28 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 25.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 1771.8390995738703,
    "paste_used_ratio": 1.0,
    "avg_label_maturity": 0.2756807268802538
  },
  "label_maturity": 0.28,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B00'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_device AND new_account, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=rule_eval_B00_1, replay_days=30)",
    "adversarial_probe(rule_id=rule_eval_B00_1, bypass_strategies=['split_contact_into_multiple_entries', 'use_different_device_with_same_ip', 'create_new_account_with_delayed_registration'])"
  ],
  "retrieval_confidence": 0.61
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Label maturity is 0.28, below the 0.5 threshold required for high-confidence fraud determination. Previous rule generation (shared_device AND new_account) was rejected due to immature labels and high confidence (0.85). Given the small suspect count (1), lack of community structure, and absence of temporal bursts or behavioral anomalies, the evidence remains insufficient for confident fraud classification. Escalation to human review is warranted to assess whether the contact overlap pattern reflects genuine fraud or legitimate user behavior, especially given the 100% paste usage and new account ratio."}, "rationale": "The diagnostic report shows a critically immature label maturity (0.28), which violates the hard constraint that fraud confidence must be tempered when maturity < 0.5. Despite pattern matches (shared contact, new accounts), the subgraph is isolated and lacks community structure or temporal clustering. The previous rule was rejected due to this immaturity. Without sufficient retrieval confidence or behavioral depth, and with only one suspect, the case lacks robustness. Escalation ensures human judgment can evaluate whether the contact overlap is part of a coordinated fraud pattern or a rare legitimate occurrence. This aligns with the guard clause that mandates escalation when retrieval confidence is low and label maturity is insufficient."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_probable", "confidence": 0.65, "recommendations": ["30-day recheck required due to immature labeling (label_maturity=0.28)", "Monitor for behavioral evolution in account activity and device sharing patterns", "Escalate to human review if new shared entity patterns emerge within 30 days"]}, "rationale": "The suspect set contains only one user with 100% new account and paste usage, and no community structure. Label maturity is 0.28, which is below the 0.5 threshold. Given the immature labeling and high confidence in fraud (previously 0.85), the confidence is downgraded to 0.65 to comply with the LABEL_MATURITY_GUARD. A 30-day recheck is recommended to validate behavioral evolution, as the current evidence is insufficient for definitive fraud confirmation. No escalation to human is triggered because the retrieval confidence is 1.0 and the case is not yet at a critical threshold for human intervention."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_B00', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_probable'}`

---

## Pair 2 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_B01",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 100%, paste used: 100%\n- Avg label maturity: 0.32 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 46.0,
    "night_apply_ratio": 1.0,
    "avg_input_speed_ms": 1364.2454827287213,
    "paste_used_ratio": 1.0,
    "avg_label_maturity": 0.32162118825527725
  },
  "label_maturity": 0.32,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B01'], hop=2, edge_type=contact)",
    "generate_rule(pattern=shared_contact AND (new_account OR night_apply OR paste_used), coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=rule_eval_B01_001, replay_days=30)",
    "adversarial_probe(rule_id=rule_eval_B01_001, bypass_strategies=['split_contact_into_multiple_entities', 'use_different_device_with_same_ip', 'create_new_account_with_delayed_registration', 'simulate_normal_input_speed'])"
  ],
  "retrieval_confidence": 0.6
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Label maturity is 0.32, below the 0.5 threshold required for high-confidence fraud determination. Previous rule generated with 0.85 confidence is invalid under the LABEL_MATURITY_GUARD. Despite strong attribute signals (100% new account, night apply, paste used), the subgraph shows no community structure and only one suspect user, making pattern validation insufficient. Retrieval confidence is 0.6, which is acceptable, but the immature label maturity prevents confident conclusion. Escalation to human investigator is required to validate the behavioral patterns and assess potential legitimate use cases or data gaps."}, "rationale": "The current investigation state violates the LABEL_MATURITY_GUARD: label_maturity (0.32) is below 0.5, and the previous rule was generated with high confidence (0.85). According to the guard, either confidence must be downgraded to 0.6-0.7, a 30-day recheck is recommended, or escalation to human is required. Given the lack of community structure, single suspect count, and absence of shared device or contact patterns beyond the initial detection, the evidence is insufficient for confident fraud confirmation. Therefore, escalation to human is the safest and most compliant action to avoid false positives or missed fraud."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_probable", "confidence": 0.65, "recommendations": ["30-day recheck required due to immature labeling (label_maturity=0.32)", "Monitor for behavioral evolution in account activity and contact patterns", "Escalate to human review if new evidence emerges within 30 days"]}, "rationale": "The alert was triggered by contact overlap among a small group of users, all exhibiting high-risk attributes (new account, night apply, paste used). However, label maturity is only 0.32, which is below the 0.5 threshold required for confident fraud determination. Given the immature labeling and high-risk behavior pattern, confidence is downgraded to 0.65 to comply with the labeling maturity guard. A 30-day recheck is recommended to observe behavioral evolution, as the current evidence is insufficient for definitive fraud confirmation. No escalation to human is triggered at this stage due to the low retrieval confidence being naturally low in small suspect sets, and the guard only applies at termination with high confidence."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_B01', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_probable'}`

---

## Pair 3 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_B02",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 100%, paste used: 100%\n- Avg label maturity: 0.20 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 40.0,
    "night_apply_ratio": 1.0,
    "avg_input_speed_ms": 2774.8133352291875,
    "paste_used_ratio": 1.0,
    "avg_label_maturity": 0.2042606468512294
  },
  "label_maturity": 0.2,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B02'], hop=2, edge_type=['contact', 'shared_device', 'ip_overlap'])",
    "generate_rule(pattern=shared_contact AND (new_account OR night_apply OR paste_used), coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=rule_eval_B02_01, replay_days=7)",
    "adversarial_probe(rule_id=rule_eval_B02_01, bypass_strategies=['split_contact_into_multiple_entries', 'use_different_device_with_same_ip', 'create_new_account_with_delayed_registration', 'simulate_normal_input_speed'])"
  ],
  "retrieval_confidence": 0.6
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Label maturity is 0.20, below the 0.5 threshold required for high-confidence fraud determination. Previous rule generated with confidence 0.85 is invalid under the LABEL_MATURITY_GUARD. Given the immature labeling and lack of community structure, the risk assessment is unstable. Manual review is required to validate the evidence and ensure no false positives or undetected patterns."}, "rationale": "The current suspect set has only 1 user, with 100% new account, night apply, and paste usage, and no community structure detected. The label maturity is 0.20, which is below the 0.5 threshold. According to the guard rule, when label_maturity < 0.5 and confidence > 0.8, we must either downgrade confidence or escalate to human. Here, the confidence was set too high (0.85) without sufficient maturity in labels. Therefore, the investigation must be escalated to human review to validate the evidence and ensure robustness before any conclusion is made."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_probable", "confidence": 0.65, "recommendations": ["30-day recheck required due to immature labeling (label_maturity=0.20)", "Monitor for behavioral evolution in account activity and contact patterns", "Escalate to human review if new evidence emerges within 30 days"]}, "rationale": "The alert was triggered by contact overlap among a single suspect user, with 100% new account, night apply, and paste usage. However, label maturity is only 0.20, which is below the 0.5 threshold. According to the guard rule, high confidence (0.85) with immature labels must be downgraded. The current confidence is reduced to 0.65 to reflect the uncertainty in labeling. A 30-day recheck is recommended to allow behavioral patterns to evolve and for labels to mature. No escalation to human is triggered at this stage due to the low suspect count and the expectation that the pattern may evolve over time. The final verdict is 'fraud_probable' with cautious confidence."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_B02', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_probable'}`

---

## Pair 4 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_B04",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 100%, paste used: 100%\n- Avg label maturity: 0.25 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 42.0,
    "night_apply_ratio": 1.0,
    "avg_input_speed_ms": 1533.6654084031684,
    "paste_used_ratio": 1.0,
    "avg_label_maturity": 0.24602527382326622
  },
  "label_maturity": 0.25,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B04'], hop=2, edge_type=['contact', 'shared_device', 'ip_overlap'])",
    "generate_rule(pattern=shared_contact AND (new_account OR night_apply OR paste_used), coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=rule_eval_B04_01, replay_days=30)",
    "adversarial_probe(rule_id=rule_eval_B04_01, bypass_strategies=['split_contact_into_multiple_entries', 'use_different_device_with_same_ip', 'create_new_account_with_delayed_registration', 'simulate_normal_input_speed'])"
  ],
  "retrieval_confidence": 0.6
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Label maturity is 0.25, below the 0.5 threshold required for high-confidence fraud determination. Previous rule generated with 0.85 confidence is invalid under the LABEL_MATURITY_GUARD. The suspect set is small (size=1) and lacks sufficient historical or structural validation. Given the immature labeling and absence of community structure, the risk assessment is not mature enough to confirm fraud with confidence. Escalation to human investigator is required to validate the pattern and assess potential legitimate explanations (e.g., isolated user behavior, technical anomalies)."}, "rationale": "The current diagnostic report shows a single suspect with 100% new account, night apply, and paste usage, but no community structure or shared entity patterns. Label maturity is only 0.25, which is below the 0.5 threshold. According to the guard rule, when label_maturity < 0.5 and confidence > 0.8, we must either downgrade confidence or escalate to human. Here, the rule was generated with 0.85 confidence, which violates the guard. Therefore, the only compliant action is to escalate to human for further investigation, especially given the isolated nature of the suspect and lack of contextual validation. This ensures that decisions are not made on immature data."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_probable", "confidence": 0.65, "recommendations": ["30-day recheck required due to immature labeling (label_maturity=0.25)", "Monitor for behavioral evolution in account activity and contact patterns", "Escalate to human review if new evidence emerges within 30 days"]}, "rationale": "The alert was triggered by contact overlap among a single suspect user, with 100% new account, night apply, and paste usage. However, label maturity is only 0.25, which is below the 0.5 threshold. According to the guard rule, high confidence (0.85) with immature labels must be downgraded. The current confidence is reduced to 0.65 to reflect the uncertainty in labeling. A 30-day recheck is recommended to observe behavioral evolution. No escalation to human is triggered here because the retrieval confidence is 1.0 and the case is not yet conclusive. The final verdict is 'fraud_probable' with cautious confidence, pending further data."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_B04', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_probable'}`

---

## Pair 5 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_C00",
  "round": 5,
  "diagnostic_report": "Alert trigger: IP shared by 8+ users flagged by rule engine\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.83 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 837.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 5175.29324966822,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.8337841915961721
  },
  "label_maturity": 0.83,
  "past_actions": [
    "expand_neighbors(seeds=['eval_C00'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=shared_ip_new_account_0, replay_days=30)",
    "adversarial_probe(rule_id=shared_ip_new_account_0, bypass_strategies=['create new account with delayed registration', 'use shared IP via rotating proxies', 'simulate normal user behavior with staggered inputs'])"
  ],
  "retrieval_confidence": 0.51
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence (0.51) is below the 0.55 threshold, indicating a novel attack pattern not well represented in historical data. The alert involves shared IP among 8+ users with no behavioral red flags (new account, night apply, paste usage), yet the subgraph shows no community structure and isolated nodes. This combination suggests a potential evasion of known fraud patterns. Given the low retrieval confidence and absence of behavioral signals, the pattern may be novel or context-dependent. Auto-termination is therefore not justified under the guard rules. Escalation to human investigator is required for contextual judgment and pattern validation."}, "rationale": "The previous attempt to terminate with fraud_confirmed was rejected due to retrieval_confidence (0.51) < 0.55, which triggers the novel pattern guard. This indicates the current pattern may not be well-covered by historical trajectories. Despite the mature label_maturity (0.83) and absence of behavioral anomalies, the lack of community structure and shared entity signals (e.g., contact, device) makes the case atypical. Without sufficient historical precedent, human review is necessary to assess whether this shared IP pattern represents legitimate usage or a previously unseen fraud vector. Escalation ensures that the investigation does not proceed with unvalidated assumptions."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.95, "recommendations": ["The alert was triggered by a shared IP among 8+ users, with no behavioral anomalies (new account, night apply, paste usage) detected.", "Subgraph analysis shows no community structure, indicating isolated users with no behavioral patterns of fraud.", "Label maturity is high (0.83), suggesting reliable historical labeling.", "All adversarial bypass strategies were tested and failed to circumvent the rule, confirming robustness.", "No red flags in input speed or account age, but shared IP remains a structural risk factor."]}, "rationale": "The suspect set contains only one user with no behavioral red flags (new account, night apply, paste used), yet the shared IP pattern is strong and consistent. The rule is validated through shadow replay and adversarial probing, showing high recall and no false positives. Label maturity is above 0.8, and retrieval confidence is 1.0. Given the structural signal (shared IP) combined with attribute signals (zero behavioral anomalies), and the absence of any bypass, the fraud is confirmed with high confidence. No human escalation is needed due to sufficient signal strength and rule validation."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_C00', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_confirmed'}`

---

## Pair 6 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_C01",
  "round": 5,
  "diagnostic_report": "Alert trigger: IP shared by 8+ users flagged by rule engine\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.93 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 576.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 3521.003841632759,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.9301504421033056
  },
  "label_maturity": 0.93,
  "past_actions": [
    "expand_neighbors(seeds=['eval_C01'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_ip AND new_account_ratio=0 AND night_apply_ratio=0, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=shared_ip_new_account_0, replay_days=30)",
    "adversarial_probe(rule_id=shared_ip_new_account_0, bypass_strategies=['create multiple accounts with staggered timestamps', 'use different IP addresses per account', 'simulate night apply via time zone manipulation', 'paste content in non-automated inputs'])"
  ],
  "retrieval_confidence": 0.5
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence is 0.50, which is below the 0.55 threshold required for auto-termination. The pattern of IP sharing among 8+ users with no behavioral anomalies (new account, night apply, paste usage) is consistent with a known benign pattern, but the low retrieval confidence indicates a potential novel attack pattern. Given the absence of structural or behavioral signals (e.g., shared device, contact) and the mature label maturity (0.93), the case lacks sufficient signal diversity to confirm fraud. Therefore, human review is required to assess whether this represents a legitimate anomaly or a sophisticated evasion strategy."}, "rationale": "The previous attempt to terminate with fraud_confirmed was rejected due to retrieval_confidence < 0.55, which triggers the novel pattern guard. This guard mandates escalation to human review when low retrieval confidence is observed during termination. The current case shows no behavioral red flags (new account, night apply, paste used) and only shared IP as a signal, with no community structure or contact overlap. While the label maturity is high, the lack of behavioral signals and the low retrieval confidence suggest uncertainty in the pattern's origin. Escalation ensures human judgment can assess whether this is a legitimate benign case or a novel fraud pattern designed to evade detection."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.95, "recommendations": ["The alert was triggered by a shared IP among 8+ users, and the subgraph shows no community structure, indicating isolated behavior.", "All attribute signals (new account, night apply, paste used) are zero, suggesting no behavioral anomalies.", "Average label maturity is 0.93, indicating mature labeling and high confidence in the signal.", "No bypass strategies succeeded in adversarial probing, confirming rule robustness.", "Retrieval confidence is 1.0, indicating full coverage and reliable retrieval of suspect data."]}, "rationale": "The investigation has completed all required rounds: neighbor expansion, rule generation, shadow replay, and adversarial probing. The subgraph shows no community structure and zero behavioral anomalies, yet the shared IP signal is strong and mature. The rule is robust and not bypassed. All hard constraints are satisfied: the rule combines structure (shared IP) and attribute (none present — but the rule pattern was designed to catch such cases), coverage_min=3, and hop=1. Given the high label maturity (0.93) and full retrieval confidence (1.0), fraud is confirmed with high confidence. No guard conditions are triggered because retrieval_confidence is 1.0 and label_maturity is above 0.5. Thus, termination with fraud_confirmed is justified."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_C01', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_confirmed'}`

---

## Pair 7 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_C02",
  "round": 5,
  "diagnostic_report": "Alert trigger: IP shared by 8+ users flagged by rule engine\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.85 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 1955.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 2897.7437971178238,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.8470665923961223
  },
  "label_maturity": 0.85,
  "past_actions": [
    "expand_neighbors(seeds=['eval_C02'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=shared_ip_new_account_0, replay_days=30)",
    "adversarial_probe(rule_id=shared_ip_new_account_0, bypass_strategies=['create new account with delayed registration', 'use shared IP via proxy rotation', 'simulate night apply by timing input', 'paste content in non-interactive mode'])"
  ],
  "retrieval_confidence": 0.52
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence (0.52) is below the 0.55 threshold, indicating a novel attack pattern that may evade existing detection logic. Previous similar trajectory (IP shared by 8+ users) resulted in escalation, and current metrics show no behavioral anomalies (new account, night apply, paste usage) despite high label maturity. Given the low retrieval confidence and absence of structural or behavioral signals, the pattern may be undetectable or intentionally obfuscated. Therefore, manual review is required to validate the legitimacy of the alert."}, "rationale": "The novel pattern guard mandates escalation when retrieval confidence < 0.55 and fraud confirmation is being considered. Despite the high label maturity (0.85) and absence of behavioral red flags, the retrieval confidence is only 0.52, signaling uncertainty in the pattern recognition. This falls under the guard condition, which requires escalation to human review instead of auto-termination. Previous similar cases with shared IP and low behavioral signals ended in escalation, reinforcing this decision. No further rule refinement or validation is justified at this stage due to insufficient retrieval confidence."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.95, "recommendations": ["The alert was triggered by a shared IP among 8+ users, with no behavioral anomalies (new account, night apply, paste usage) detected in the suspect set.", "Subgraph analysis shows no community structure, indicating isolated behavior consistent with potential fraud.", "Label maturity is high (0.85), suggesting strong historical signal for fraud patterns.", "All adversarial bypass strategies were successfully blocked, confirming rule robustness.", "No evidence of legitimate user behavior, and the combination of shared IP (structure) with zero behavioral anomalies (attribute) meets rule criteria."]}, "rationale": "The investigation has completed all required rounds: neighbor expansion, rule generation, shadow replay, and adversarial probing. The suspect set is small (n=1), with no behavioral signals (new account, night apply, paste used), yet the shared IP structure is present and mature. The rule combines a structural signal (shared IP) with an attribute signal (zero behavioral anomalies), meeting coverage_min=3 and confidence_threshold=0.9. Retrieval confidence is 1.0, and no guard conditions are triggered (label_maturity=0.85 ≥ 0.5, retrieval_confidence=1.0 ≥ 0.55). Therefore, fraud is confirmed with high confidence. All validation steps have been satisfied, and no further action is needed."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_C02', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_confirmed'}`

---

## Pair 8 — verdict_based

### Prompt
```
# Current investigation state

{
  "alert_id": "eval_C03",
  "round": 5,
  "diagnostic_report": "Alert trigger: IP shared by 8+ users flagged by rule engine\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.75 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 226.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 3554.350577938571,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.7459888481546162
  },
  "label_maturity": 0.75,
  "past_actions": [
    "expand_neighbors(seeds=['eval_C03'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=shared_ip_new_account_0, replay_days=30)",
    "adversarial_probe(rule_id=shared_ip_new_account_0, bypass_strategies=['create new account with different IP', 'use shared device to mask new account', 'simulate night apply via delayed form submission'])"
  ],
  "retrieval_confidence": 0.51
}

Return next action as JSON.
```

### Chosen
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence (0.51) is below the 0.55 threshold, indicating a novel attack pattern not well represented in historical data. Previous similar trajectory (IP shared by 8+ users) resulted in escalation, and current metrics show no behavioral anomalies (new account, night apply, paste used) despite high label maturity. Given the low retrieval confidence and absence of structural or behavioral signals, the risk profile is ambiguous. Auto-termination would be premature and potentially misaligned with real-world fraud dynamics. Human review is required to validate whether the shared IP pattern represents legitimate usage or a coordinated fraud attempt."}, "rationale": "The novel pattern guard mandates escalation when retrieval confidence < 0.55 and fraud confirmation is being considered. Despite the alert being triggered by shared IP and the suspect set being small, the absence of any behavioral red flags (new account, night apply, paste) and the lack of community structure suggest a low-risk profile. However, the retrieval confidence is insufficient to trust the pattern match against historical data. The previous similar case with 8+ shared IPs ended in escalation, reinforcing that such cases require human judgment. Therefore, escalation to human review is the safest and most compliant action under the guard rules."}
```

### Rejected
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.95, "recommendations": ["The alert was triggered by a shared IP among 8+ users, with no behavioral anomalies (new account, night apply, paste usage) detected.", "Subgraph analysis shows isolated users with no community structure, indicating low connectivity and potential synthetic behavior.", "Label maturity of 0.75 indicates mature labeling, supporting the reliability of the detection.", "Rule validation via shadow replay and adversarial probing confirmed robustness against common bypass strategies.", "No evidence of behavioral deviation or synthetic account creation; however, high IP sharing among users suggests potential fraud risk."]}, "rationale": "The investigation has completed all required rounds: neighbor expansion, rule generation, shadow replay, and adversarial probing. All actions have been executed successfully. The subgraph shows no community structure, and all attribute signals (new account, night apply, paste) are zero. Despite the absence of behavioral anomalies, the shared IP pattern among 8+ users is a strong structural signal. The rule combines a structural signal (shared IP) with attribute signals (all zero), meeting coverage_min=3 and confidence_threshold=0.9. Shadow replay and adversarial probing confirm the rule is not easily bypassed. Retrieval confidence is 1.0, and label maturity is 0.75, both above thresholds. No guard conditions are triggered (label_maturity >= 0.5 and retrieval_confidence >= 0.55). Therefore, fraud is confirmed with high confidence based on the structural signal and rule validation."}
```

### Meta
`{'source': 'verdict_based', 'alert_id': 'eval_C03', 'round': 5, 'correct_verdict': 'escalate', 'wrong_verdict': 'fraud_confirmed'}`

---

