# DPO Pairs — ACRM-style Samples

## Pair 1 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_B05', 'round': 5, 'score_diff': 0.85, 'better_score': 0.975, 'worse_score': 0.125, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_B05",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.25 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 17.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 1213.8785162960128,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.24731108637784757
  },
  "label_maturity": 0.25,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B05'], hop=1, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_device AND new_account, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=rule_001, replay_days=30)",
    "adversarial_probe(rule_id=rule_001, bypass_strategies=['split_contact_into_multiple_entities', 'use_shared_device_with_different_device_id', 'create_new_account_with_delayed_registration'])"
  ],
  "retrieval_confidence": 1.0
}

Retur...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.75, "recommendations": ["30-day recheck required due to low label maturity (0.25)", "Monitor for potential reapplication or device sharing patterns", "Escalate to human review for further validation of account legitimacy"]}, "rationale": "The suspect set consists of a single user with 100% new account ratio and no behavioral anomalies (no night apply, no paste usage). Despite the detection of contact overlap, the subgraph shows no community structure and is isolated. The rule generated (shared_device AND new_account) has high confidence (0.85) and coverage_min=3, but label maturity is only 0.25, which is below the threshold for high confidence. According to the hard constraints, when label_maturity < 0.5 and confidence > 0.8, we must downgrade confidence to 0.75 and add a 30-day recheck. The retrieval_confidence is 1.0, so no escalation is needed. Final verdict is fraud_confirmed with reduced confidence and explicit recheck recommendation."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Alert trigger shows contact overlap among isolated users with immature label maturity (0.25 < 0.5) and high confidence (0.85) in rule generation. This violates the LABEL_MATURITY_GUARD: when label_maturity < 0.5 and confidence > 0.8, either confidence must be downgraded to 0.6-0.7 or escalation to human is required. Given the lack of structural validation (no community, no temporal bursts) and minimal historical signal, the current rule is unsupported by mature labeling. Thus, human review is necessary to validate the fraud potential without risking false positives or missed cases."}, "rationale": "The previous rule (shared_contact AND new_account) was generated with high confidence (0.85) despite the label maturity being only 0.25, which is below the 0.5 threshold. According to the guard rule, such a high-confidence conclusion on immature data must be mitigated. Since the subgraph shows no community structure, no temporal bursts, and only one suspect, the evidence is insufficient for confident fraud determination. Escalation to human review is therefore required to validate the actual fraud pattern, especially given the absence of shared device or IP patterns and the minimal retrieval confidence (0.61)."}
```

---

## Pair 2 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_B05', 'round': 5, 'score_diff': 0.85, 'better_score': 0.975, 'worse_score': 0.125, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_B05",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.25 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 17.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 1213.8785162960128,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.24731108637784757
  },
  "label_maturity": 0.25,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B05'], hop=2, edge_type=contact)",
    "generate_rule(pattern=shared_contact AND new_account, coverage_min=3, confidence_threshold=0.8)",
    "shadow_replay(rule_id=rule_eval_B05_1, replay_days=30)",
    "adversarial_probe(rule_id=rule_eval_B05_1, bypass_strategies=['split_contact_into_multiple_entries', 'use_different_device_with_same_ip', 'create_new_account_with_delayed_registration'])"
  ],
  "retrieval_confidence": 0.61
}

Return next action as JSON....
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.75, "recommendations": ["30-day recheck required due to low label maturity (0.25)", "Monitor for re-emergence of contact overlap or new account patterns", "Flag for manual review if additional behavioral signals appear"]}, "rationale": "The alert was triggered by contact overlap among a small group of users, with 100% new accounts and no night apply or paste usage. A rule combining shared contact (structure) and new account (attribute) was generated and validated via shadow replay and adversarial probe. Past similar cases with contact overlap resulted in fraud confirmation. Despite low label maturity (0.25), the pattern is consistent with known fraud signals. However, given the low maturity and the small suspect count (1), the confidence is capped at 0.75 to reflect uncertainty. A 30-day recheck is recommended to ensure stability and avoid false positives. No escalation to human is needed as the pattern is well-supported by historical trajectories and rule validation."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Alert trigger shows contact overlap among isolated users with immature label maturity (0.25 < 0.5) and high confidence (0.85) in rule generation. This violates the LABEL_MATURITY_GUARD: when label_maturity < 0.5 and confidence > 0.8, either confidence must be downgraded to 0.6-0.7 or escalation to human is required. Given the lack of structural validation (no community, no temporal bursts) and minimal historical signal, the current rule is unsupported by mature labeling. Thus, human review is necessary to validate the fraud potential without risking false positives or missed cases."}, "rationale": "The previous rule (shared_contact AND new_account) was generated with high confidence (0.85) despite the label maturity being only 0.25, which is below the 0.5 threshold. According to the guard rule, such a high-confidence conclusion on immature data must be mitigated. Since the subgraph shows no community structure, no temporal bursts, and only one suspect, the evidence is insufficient for confident fraud determination. Escalation to human review is therefore required to validate the actual fraud pattern, especially given the absence of shared device or IP patterns and the minimal retrieval confidence (0.61)."}
```

---

## Pair 3 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_B05', 'round': 5, 'score_diff': 0.85, 'better_score': 0.975, 'worse_score': 0.125, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_B05",
  "round": 5,
  "diagnostic_report": "Alert trigger: Contact overlap detected among small user group\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 100%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.25 (IMMATURE)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 1.0,
    "avg_account_age_days": 17.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 1213.8785162960128,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.24731108637784757
  },
  "label_maturity": 0.25,
  "past_actions": [
    "expand_neighbors(seeds=['eval_B05'], hop=2, edge_type=contact)",
    "generate_rule(pattern=shared_contact AND new_account, coverage_min=3, confidence_threshold=0.8)",
    "shadow_replay(rule_id=rule_eval_B05_shared_contact_new_account, replay_days=30)",
    "adversarial_probe(rule_id=rule_eval_B05_shared_contact_new_account, bypass_strategies=['create new account with different device and contact', 'use shared contact from a known non-fraudulent user', 'simulate multiple accounts with stagg...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "fraud_confirmed", "confidence": 0.75, "recommendations": ["30-day recheck required due to low label maturity (0.25)", "Monitor for device or contact overlap expansion in next 7 days", "Escalate to human review if new accounts or contact patterns emerge"]}, "rationale": "The alert was triggered by contact overlap among a small group of users, with 100% new accounts and no night apply or paste usage. Despite low label maturity (0.25), the pattern matches a known trajectory (contact overlap → fraud_confirmed) with 61% similarity to a prior case. The generated rule (shared_contact AND new_account) passed shadow replay and adversarial probe without bypass. However, due to low maturity and limited historical signal, the confidence is capped at 0.75. The guard condition (label_maturity < 0.5 and confidence > 0.8) is triggered, so we downgrade confidence and add a 30-day recheck recommendation. Retrieval confidence (0.61) is sufficient for termination at this stage, as it is not below 0.55 and the case has a clear pattern match with prior fraud cases."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Alert trigger shows contact overlap among isolated users with immature label maturity (0.25 < 0.5) and high confidence (0.85) in rule generation. This violates the LABEL_MATURITY_GUARD: when label_maturity < 0.5 and confidence > 0.8, either confidence must be downgraded to 0.6-0.7 or escalation to human is required. Given the lack of structural validation (no community, no temporal bursts) and minimal historical signal, the current rule is unsupported by mature labeling. Thus, human review is necessary to validate the fraud potential without risking false positives or missed cases."}, "rationale": "The previous rule (shared_contact AND new_account) was generated with high confidence (0.85) despite the label maturity being only 0.25, which is below the 0.5 threshold. According to the guard rule, such a high-confidence conclusion on immature data must be mitigated. Since the subgraph shows no community structure, no temporal bursts, and only one suspect, the evidence is insufficient for confident fraud determination. Escalation to human review is therefore required to validate the actual fraud pattern, especially given the absence of shared device or IP patterns and the minimal retrieval confidence (0.61)."}
```

---

## Pair 4 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_C05', 'round': 5, 'score_diff': 0.85, 'better_score': 0.972, 'worse_score': 0.122, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_C05",
  "round": 5,
  "diagnostic_report": "Alert trigger: IP shared by 8+ users flagged by rule engine\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.96 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 246.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 1389.3004788498215,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.9577567116164708
  },
  "label_maturity": 0.96,
  "past_actions": [
    "expand_neighbors(seeds=['eval_C05'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=shared_ip_new_account_0, replay_days=30)",
    "adversarial_probe(rule_id=shared_ip_new_account_0, bypass_strategies=['create new account with different IP', 'use shared device to mask new account', 'simulate night apply via time zone manip...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "not_fraud", "confidence": 0.87, "recommendations": ["No behavioral anomalies detected (new account, night apply, paste usage) despite shared IP.", "High label maturity (0.96) suggests reliable labeling in this subgraph.", "Similar past case with 12 users shared IP and concluded not fraud (similarity 0.51).", "No evidence of structural or behavioral fraud patterns beyond shared IP."]}, "rationale": "The suspect set consists of only 1 user with no behavioral red flags (new account, night apply, paste used), and the shared IP pattern is common and non-anomalous. The subgraph shows no community structure or temporal bursts. The rule generated (shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0) is validated by shadow replay with no false positives. Adversarial probe failed to bypass the rule due to the absence of behavioral anomalies. Given the high label maturity (0.96) and absence of any attribute signals, the case does not meet the threshold for fraud. Past similar cases with shared IP and no behavioral anomalies concluded as not fraud. Retrieval confidence (0.51) is acceptable given the small suspect set and mature labeling. No guard conditions are triggered (label_maturity >= 0.5, retrieval_confidence >= 0.55). Therefore, termination with not_fraud is justified."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence is 0.50, which is below the 0.55 threshold required for auto-termination. The pattern of IP sharing by 8+ users with no behavioral red flags (new account, night apply, paste usage) is novel and may indicate an evasion tactic. Previous similar case with 12 shared IPs was labeled 'not_fraud' with low confidence, while this case has high label maturity (0.96) and no behavioral anomalies. Given the low retrieval confidence and absence of structural or behavioral signals beyond shared IP, the risk profile is ambiguous. Escalation to human review is required to assess whether this represents a legitimate user pattern or a targeted attack."}, "rationale": "The current trajectory has a retrieval confidence of 0.50, which violates the hard constraint that retrieval_confidence < 0.55 must trigger escalation to human when terminating with fraud_confirmed. Although the alert was triggered by shared IP and the subgraph shows no community structure or behavioral anomalies, the low retrieval confidence indicates a novel or unmodeled pattern. The absence of any attribute signals (new account, night apply, paste) and the high label maturity suggest a mature, possibly legitimate user profile. However, without sufficient retrieval confidence, auto-termination is not justified. Therefore, the case must be escalated to human investigators for contextual review to determine if this represents a legitimate user or a sophisticated evasion pattern."}
```

---

## Pair 5 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_C05', 'round': 5, 'score_diff': 0.85, 'better_score': 0.972, 'worse_score': 0.122, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_C05",
  "round": 5,
  "diagnostic_report": "Alert trigger: IP shared by 8+ users flagged by rule engine\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.96 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 246.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 1389.3004788498215,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.9577567116164708
  },
  "label_maturity": 0.96,
  "past_actions": [
    "expand_neighbors(seeds=['eval_C05'], hop=2, edge_type=['shared_device', 'shared_ip', 'contact'])",
    "generate_rule(pattern=shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0, coverage_min=3, confidence_threshold=0.85)",
    "shadow_replay(rule_id=shared_ip_new_account_0, replay_days=30)",
    "adversarial_probe(rule_id=shared_ip_new_account_0, bypass_strategies=['create new account with different IP', 'use shared device to mask new account', 'simulate night apply via time zone manip...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "not_fraud", "confidence": 0.87, "recommendations": ["No behavioral anomalies detected (new account, night apply, paste usage) despite shared IP.", "High label maturity (0.96) suggests reliable labeling in this subgraph.", "Similar past case with 12 users shared IP and concluded not fraud (similarity 0.51).", "No evidence of structural or behavioral fraud patterns beyond shared IP."]}, "rationale": "The suspect set consists of only 1 user with no behavioral red flags (new account, night apply, paste used), and the shared IP pattern is common and non-anomalous. The subgraph shows no community structure or temporal bursts. The rule generated (shared_ip AND new_account_ratio == 0 AND night_apply_ratio == 0) is validated by shadow replay with no false positives. Adversarial probe failed to bypass the rule due to the absence of behavioral anomalies. Given the high label maturity (0.96) and absence of any attribute signals, the case does not meet the threshold for fraud. Past similar cases with shared IP and no behavioral anomalies concluded as not fraud. Retrieval confidence (0.51) is acceptable given the small suspect set and mature labeling. No guard conditions are triggered (label_maturity >= 0.5, retrieval_confidence >= 0.55). Therefore, termination with not_fraud is justified."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence (0.51) is below the 0.55 threshold, indicating a novel attack pattern not well represented in historical data. The alert involves shared IP among 8+ users with no behavioral anomalies (new account, night apply, paste usage), yet the subgraph shows no community structure and isolated nodes. This combination suggests a low-visibility fraud pattern that may evade standard detection logic. Given the low retrieval confidence and absence of clear structural or behavioral signals, manual investigation is required to validate whether this is a legitimate user behavior or a coordinated fraud attempt."}, "rationale": "The previous attempt to terminate with fraud_confirmed was rejected due to retrieval_confidence (0.51) < 0.55, which triggers the novel pattern guard. This indicates the current case may involve an attack pattern not seen in past trajectories. Since the subgraph lacks community structure and behavioral anomalies, and the only signal is shared IP (a common benign signal), the possibility of a novel, low-visibility fraud pattern exists. Escalating to human review ensures that contextual and behavioral nuances are assessed beyond automated rules, especially when historical data is insufficient to support confidence in an automated verdict."}
```

---

## Pair 6 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_D03', 'round': 5, 'score_diff': 0.85, 'better_score': 0.972, 'worse_score': 0.122, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_D03",
  "round": 5,
  "diagnostic_report": "Alert trigger: Anomaly detector flagged high-amount application\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.94 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 1168.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 4076.835365971774,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.9409168653673536
  },
  "label_maturity": 0.94,
  "past_actions": [
    "expand_neighbors(seeds=['eval_D03'], hop=2, edge_type=application)",
    "generate_rule(pattern=high-amount application AND isolated user, coverage_min=3, confidence_threshold=0.8)",
    "shadow_replay(rule_id=high-amount application AND isolated user, replay_days=30)",
    "adversarial_probe(rule_id=high-amount application AND isolated user, bypass_strategies=['use different device', 'apply during day', 'lower application amount'])"
  ],
  "retrieval_confidence": 0.4
}

Return next action as J...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "not_fraud", "confidence": 0.6, "recommendations": "30-day recheck required"}, "rationale": "The investigation shows that the suspect user has a high label maturity (0.94) and no concerning patterns (new account ratio, night apply, paste used are all 0). Despite the high-amount application being flagged, the context suggests that this user does not fit the fraud profile, leading to a not_fraud conclusion with a recommendation for a 30-day recheck."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence (0.43) is below the 0.55 threshold required for confident auto-termination. The pattern observed — a high-amount application with no behavioral anomalies (new account, night apply, paste use) and mature label maturity — is novel and not well-represented in historical data. Given the low retrieval confidence and absence of clear structural or behavioral signals, this case may involve an evasion tactic or a legitimate user with atypical behavior. Escalation to human review is necessary to validate the legitimacy and assess potential bypass mechanisms."}, "rationale": "The previous attempt to terminate with fraud_confirmed was rejected due to retrieval_confidence (0.43) < 0.55, which triggers the novel pattern guard. This indicates the current pattern is not well-supported by historical data, and the absence of behavioral anomalies (e.g., night apply, paste use) despite high-amount application suggests either a legitimate user or a sophisticated evasion strategy. Without sufficient historical precedent, auto-termination is not justified. Escalation to human review ensures proper contextual evaluation and prevents false positives or missed fraud signals."}
```

---

## Pair 7 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_D03', 'round': 5, 'score_diff': 0.85, 'better_score': 0.972, 'worse_score': 0.122, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_D03",
  "round": 5,
  "diagnostic_report": "Alert trigger: Anomaly detector flagged high-amount application\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.94 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 1168.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 4076.835365971774,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.9409168653673536
  },
  "label_maturity": 0.94,
  "past_actions": [
    "expand_neighbors(seeds=['eval_D03'], hop=2, edge_type=application)",
    "generate_rule(pattern=high-amount application AND isolated user, coverage_min=3, confidence_threshold=0.8)",
    "shadow_replay(rule_id=high-amount application AND isolated user, replay_days=30)",
    "adversarial_probe(rule_id=high-amount application AND isolated user, bypass_strategies=['use different device', 'apply during day', 'lower application amount'])"
  ],
  "retrieval_confidence": 0.4
}

Return next action as J...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "not_fraud", "confidence": 0.6, "recommendations": "30-day recheck required"}, "rationale": "The investigation shows that the suspect user has a high label maturity (0.94) and no concerning patterns (new account ratio, night apply, paste used are all 0). Despite the high-amount application being flagged, the context suggests that this user does not fit the fraud profile, leading to a not_fraud conclusion with a recommendation for a 30-day recheck."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence (0.43) is below the 0.55 threshold required for auto-termination, indicating a novel or atypical attack pattern. The suspect set is isolated with no community structure, and all behavioral signals (new account, night apply, paste use) are zero, yet the label maturity is high (0.94). This combination suggests either a legitimate high-value user or an undetected evasion pattern. Given the low retrieval confidence and absence of clear structural or behavioral signals, the risk of false positive or novel fraud is elevated. Therefore, human review is required to validate the context and determine whether the alert represents a genuine threat or a legitimate user behavior."}, "rationale": "The previous attempt to terminate with fraud_confirmed was rejected due to retrieval_confidence (0.43) < 0.55, which triggers the novel pattern guard. This threshold is critical because low retrieval confidence implies insufficient data grounding for the conclusion. In this case, despite high label maturity and a mature signal profile, the absence of any behavioral anomalies (new account, night apply, paste use) and the isolated subgraph structure suggest no clear fraud pattern. Without sufficient retrieval confidence, auto-termination is unsafe. Escalation to human review ensures contextual understanding and prevents false positives or missed legitimate cases. This aligns with the guard rule that applies only at termination and only when retrieval_confidence < 0.55 and fraud_confirmed is intended."}
```

---

## Pair 8 — accepted_vs_accepted

**Meta**: `{'source': 'accepted_vs_accepted', 'alert_id': 'eval_D03', 'round': 5, 'score_diff': 0.85, 'better_score': 0.972, 'worse_score': 0.122, 'sim_type': 'same_alert'}`

### Prompt
```
# Current investigation state
{
  "alert_id": "eval_D03",
  "round": 5,
  "diagnostic_report": "Alert trigger: Anomaly detector flagged high-amount application\nSubgraph analysis of 1 suspect users:\n- No community structure detected (isolated or sparsely connected).\n- New account ratio: 0%, night apply: 0%, paste used: 0%\n- Avg label maturity: 0.94 (mature)",
  "suspect_count": 1,
  "key_metrics": {
    "suspect_count": 1,
    "new_account_ratio": 0.0,
    "avg_account_age_days": 1168.0,
    "night_apply_ratio": 0.0,
    "avg_input_speed_ms": 4076.835365971774,
    "paste_used_ratio": 0.0,
    "avg_label_maturity": 0.9409168653673536
  },
  "label_maturity": 0.94,
  "past_actions": [
    "expand_neighbors(seeds=['eval_D03'], hop=2, edge_type=application)",
    "generate_rule(pattern=high-amount application AND isolated user, coverage_min=3, confidence_threshold=0.8)",
    "shadow_replay(rule_id=high-amount application AND isolated user, replay_days=30)",
    "adversarial_probe(rule_id=high-amount application AND isolated user, bypass_strategies=['use different device', 'apply during day', 'lower application amount'])"
  ],
  "retrieval_confidence": 0.4
}

Return next action as J...
```

### Chosen
```json
{"action_type": "terminate", "params": {"verdict": "not_fraud", "confidence": 0.6, "recommendations": "30-day recheck required"}, "rationale": "The investigation shows that the suspect user has a high label maturity (0.94) and no concerning patterns (new account ratio, night apply, paste used are all 0). Despite the high-amount application being flagged, the context suggests that this user does not fit the fraud profile, leading to a not_fraud conclusion with a recommendation for a 30-day recheck."}
```

### Rejected
```json
{"action_type": "escalate_to_human", "params": {"reason": "Retrieval confidence is 0.42, below the 0.55 threshold required for confident auto-termination. This suggests a novel or atypical attack pattern that may not be captured by existing rules or patterns. Given the isolated subgraph, absence of behavioral anomalies (new account, night apply, paste used), and high label maturity (0.94), the fraud signal is weak but the pattern is novel. The low retrieval confidence indicates insufficient evidence linkage from historical data, necessitating human review to assess whether the high-amount application is legitimate or part of a stealthy pattern. Previous similar trajectories show mixed outcomes (fraud confirmed, not fraud, escalate), supporting the need for human judgment."}, "rationale": "The current retrieval_confidence (0.42) is below the 0.55 guard threshold. According to the hard constraints, when retrieval_confidence < 0.55 and fraud is about to be confirmed, the system must escalate to human review instead of terminating automatically. This case presents a novel anomaly with no behavioral signals (0% new account, night apply, paste used), yet a high label maturity, suggesting maturity in user profile but no behavioral red flags. The lack of shared structure signals (no contact, shared device, shared IP) and absence of behavioral anomalies further reduce confidence in automated detection. Given the small suspect set (1 user) and no community structure, the signal is weak. Thus, escalation is required to avoid false positives or missed fraud in a novel pattern."}
```

---

