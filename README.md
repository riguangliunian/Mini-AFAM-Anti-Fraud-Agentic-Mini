# Mini AFAM — 反欺诈模型衰退诊断 Agent

Mini AFAM 是一个面向**反欺诈线上模型效果衰退诊断与修复策略推荐**的 Agent 原型。它不是替代欺诈评分模型，也不是直接判断某个用户是否欺诈；它模拟的是资深反欺诈算法工程师在收到线上模型监控告警后，如何一步步排查根因、调用诊断工具、选择修复策略、验证上线风险，并决定自动修复、延迟决策或升级人工。

项目参考了 ACRM 的 trajectory learning 思路，但把任务从“信用模型刷新”迁移到了“反欺诈模型衰退诊断”。

```text
线上模型告警
    -> Diagnosis State
    -> LLM Planner / Orchestrator
    -> RuleStream 校验
    -> Specialist Tools 执行
    -> Tool Outcome
    -> 更新 State
    -> 修复 / 延迟 / 人工复核
    -> 保存 Trajectory Memory
```

---

## 1. 项目要解决什么问题

反欺诈模型线上效果下降，不一定是模型本身坏了。指标下降背后可能是：

- 上游数据链路故障；
- 特征分布漂移；
- 流量客群迁移；
- 固定阈值失准；
- 黑产攻击方式变化；
- 标签延迟；
- 规则交互污染评估样本；
- 模型容量不足，需要重新训练。

因此，这个 Agent 重点回答：

```text
模型为什么衰退？
下一步应该查什么证据？
应该 feature patch、调阈值、更新规则、局部重训、全量重训，还是等待标签成熟？
这个修复能否安全上线？
什么情况下应该升级人工？
```

项目把一次诊断过程建模为多轮轨迹：

```text
τ = {(state_t, action_t, outcome_t)}^T
```

每条轨迹都可以审计、回放，并用于后续 SFT/DPO 专家偏好对齐。

---

## 2. Agent 范式

这是一个 **Plan-and-Execute 架构下的 Agent Loop**。

它不是一次性生成完整计划，而是每轮只规划下一步动作：

```text
观察当前 Diagnosis State
    ↓
LLM Planner 生成一个语义级 Action
    ↓
RuleStream 做硬校验
    ↓
Specialist Tool 执行
    ↓
得到 Outcome
    ↓
更新 State
    ↓
继续诊断 / 修复 / 延迟 / 人工复核 / 终止
```

它结合了几类 Agent 范式：

| 范式 | 在项目里的体现 |
|---|---|
| Planner-Executor | LLM Orchestrator 负责规划，确定性 Tool 负责执行 |
| ReAct-style Loop | 每轮 Observe -> Plan -> Act -> Observe |
| Generate-then-Validate | LLM 生成 Action JSON，RuleStream 拒绝不安全动作 |
| Retrieval-Augmented Agent | 检索 Top-K 历史专家轨迹作为 few-shot context |
| Trajectory Learning | 保存完整 State-Action-Outcome，用于后续 SFT/DPO |
| Safety-Constrained Agent | 用硬规则防止误修、reward hacking、跳过 replay |
| Human-in-the-loop Agent | 不确定或高风险场景升级人工 |

---

## 3. 系统架构

```text
┌─────────────────────────────────────────────────────────────┐
│ 线上模型监控告警                                             │
│ metric_drop / affected_segments / monitor_alert / budget    │
└───────────────────────────────┬─────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│ Diagnosis State                                              │
│ 模型健康、稳定性信号、证据、假设、修复候选、replay、历史动作    │
└───────────────────────────────┬─────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│ Hybrid Knowledge Layer                                       │
│ RuleStream + Trajectory Retrieval + DPO-ready Alignment      │
└───────────────────────────────┬─────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM Planner / Orchestrator                                   │
│ 生成一个语义级 Diagnosis Action JSON                         │
└───────────────────────────────┬─────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│ RuleStream                                                   │
│ 校验证据、replay、预算、标签成熟度、安全上线约束               │
└───────────────────────────────┬─────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│ Specialist Tool Layer                                        │
│ SQL / DQ / PSI / SHAP / Behavior / Graph / Replay            │
└───────────────────────────────┬─────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────┐
│ Outcome -> State Update -> Trajectory Memory                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Diagnosis State 设计

每条线上告警会被初始化为结构化 `DiagnosisState`。注意：`root_cause` 和 `expected_repair` 是评测集里的标准答案，只用于离线评测，不会提供给 LLM，避免信息泄露。

典型字段：

| 字段 | 含义 |
|---|---|
| `metric_drop` | 模型指标下降，例如 recall、precision、amount recall |
| `affected_segments` | 指标下降集中在哪些局部客群，例如安卓端、新客、夜间申请 |
| `monitor_alert` | 数据质量、PSI、SHAP、行为、图模式、规则命中、标签成熟度等监控信号 |
| `evidence` | 工具收集到的证据 |
| `hypotheses` | 当前根因假设及置信度 |
| `repair_candidate` | 当前修复候选 |
| `replay` | 回放 / shadow 验证结果 |
| `action_history` | 已调用动作和结果 |
| `remaining_budget` | 当前诊断剩余工具预算 |

示例：

```json
{
  "alert_id": "diag_attack_01",
  "model_name": "fraud_ranker",
  "metric_drop": {
    "recall_at_fpr": -0.19,
    "precision": -0.04,
    "amount_recall": -0.20
  },
  "affected_segments": {
    "old_accounts": -0.23
  },
  "monitor_alert": {
    "behavior_shift": 0.24,
    "graph_shift": 0.31,
    "label_maturity": 0.72
  },
  "evidence": [],
  "hypotheses": [],
  "remaining_budget": 10.0
}
```

---

## 5. 语义级 Action Space

LLM 不能自由写 SQL、训练代码或规则代码，只能从固定的语义级动作中选择。这样可以把 LLM 限制在“决策层”，底层事实计算由确定性工具完成。

诊断动作：

```text
analyze_segment_drop
run_sql_profile
check_data_quality
compute_feature_psi
analyze_shap_shift
analyze_behavior_sequence_shift
analyze_graph_pattern_shift
check_label_maturity
```

修复 / 验证 / 终止动作：

```text
propose_feature_patch
adjust_threshold
update_rule
recommend_partial_retraining
recommend_full_retraining
run_replay_backtest
terminate
escalate_to_human
```

典型映射：

| 根因 | 期望修复 |
|---|---|
| 数据链路故障 | `feature_patch` |
| 特征分布漂移 | `partial_retraining` |
| 客群迁移 / 阈值失准 | `threshold_adjustment` |
| 黑产攻击方式变化 | `rule_update` |
| 标签延迟 | `defer_until_label_mature` |
| 模型容量不足 | `full_retraining` |

---

## 6. RuleStream

RuleStream 是硬约束层，不是 prompt 里的软提醒。LLM 生成候选 action 后，RuleStream 会校验是否满足生产约束；如果违规，会把明确错误反馈给 LLM 重试。

典型规则：

| 规则 | 防止的风险 |
|---|---|
| 修复前必须有足够证据 | 防止看到指标下降就盲目 patch / retrain |
| 修复后必须 replay | 防止未验证的规则或阈值直接上线 |
| 标签不成熟时禁止直接重训 | 防止用未成熟标签污染模型 |
| full retraining 不能过早触发 | 防止高成本、无必要的全量重训 |
| 工具调用类 case 必须调用 required tools | 防止 shortcut reasoning |
| forbidden actions 一票否决 | 防止不安全动作 |
| 不能超出工具预算 | 控制诊断成本 |
| 稳定性 / 误伤 / coverage 护栏 | 防止 reward hacking 和不安全上线 |

典型 reward hacking：

```text
Agent 为了让整体指标变好，试图排除高风险、难识别的安卓新客 segment。
RuleStream 会检查 segment coverage loss、PSI、样本覆盖变化。
如果覆盖损失或稳定性恶化超限，该 action 会被拒绝。
```

---

## 7. Trajectory Retrieval

当前原型使用轻量 TF-IDF 检索历史轨迹摘要。

历史轨迹摘要包含：

- 初始告警 / State 摘要；
- 关键证据；
- action sequence；
- diagnosed root cause；
- repair strategy；
- final outcome。

当前 State 会被转成同样的文本表示，然后通过 TF-IDF cosine similarity 召回 Top-3 历史轨迹，作为 few-shot context。

当前局限：

```text
TF-IDF 简单、可解释，适合小规模原型；
但它只看词面重合，不理解语义，也不擅长表达轨迹结构。
生产版本应升级为 dense embedding + metadata filter + rerank 的 hybrid retrieval。
```

---

## 8. 评测场景

当前 production diagnosis benchmark 包含 **40 条合成但业务合理的评测 case**，分为五类。

| 类别 | 数量 | 评测什么 | 期望修复 |
|---|---:|---|---|
| A_DataIntegrity | 6 | 数据链路故障：特征缺失、schema 变更、上游延迟、实体解析错误 | `feature_patch` |
| B_DistributionShift | 12 | 分布漂移：特征漂移、客群迁移、阈值失准、模型容量不足 | `partial_retraining` / `threshold_adjustment` / `full_retraining` |
| C_AdversarialDrift | 6 | 对抗漂移：黑产行为变化、图模式迁移、新型绕过攻击 | `rule_update` |
| D_FeedbackLoop | 8 | 反馈闭环：标签延迟、人工审核滞后、规则交互污染样本 | `defer_until_label_mature` / `rule_update` |
| E_AgentToolUse | 8 | Agent 工具调用能力：required tools、forbidden actions、预算、replay、流程纪律 | 答案正确 + 流程合规 |

---

## 9. 评测指标

评测分三层。

### 9.1 Agent 决策与执行能力

| 指标 | 含义 |
|---|---|
| Root-cause Accuracy | 根因诊断是否正确 |
| Repair Strategy Accuracy | 修复策略是否正确 |
| Joint Success | 根因和修复是否同时正确 |
| Process Success | 工具调用流程、预算、required / forbidden action 是否合规 |
| Overall Success | Task Success 和 Process Success 是否同时成立 |
| Average Rounds | 平均诊断轮数 |
| Average Tool Cost | 平均工具成本 |
| Premature Fix Rate | 证据或 replay 不足时就修复的比例 |
| Human Handover Rate | 升级人工比例 |

### 9.2 业务刷新指标

| 指标 | 含义 |
|---|---|
| Expected Metric Recovery | 预期模型指标恢复比例 |
| Recall Recovery | 主召回指标恢复比例 |
| Stability Violation Rate | PSI / FP / coverage 护栏违规比例 |
| Average Coverage Loss | 修复导致的人群覆盖损失 |
| False-positive Impact | 修复带来的误伤影响 |
| Review Workload Change | 对人工审核量的影响 |
| Repair Acceptance Rate | 修复方案是否可被生产审核接受 |

### 9.3 反欺诈专项生产指标

| 指标 | 含义 |
|---|---|
| Fraud Recall Recovery | 欺诈召回恢复比例 |
| Amount Recall Recovery | 高金额风险召回恢复比例 |
| Segment-level Recovery | 受影响局部客群恢复比例 |
| Novel Attack Detection Rate | 新型攻击 / 对抗漂移识别率 |
| Label Maturity Guard Accuracy | 标签不成熟时是否避免误修 |
| Rule Robustness / Bypass Resistance | 规则更新是否经过 replay，是否具备抗绕过性 |
| Safe Deployment Rate | 修复是否满足上线要求：答案正确、流程合规、稳定、低误伤 |
| Avg Time-to-Mitigation | 从告警到形成缓解方案的估计耗时 |

---

## 10. 最新评测结果

真实 LLM 评测配置：

```text
Model: gpt-4o-mini
Modes: zero-shot baseline vs retrieval few-shot
Cases: 40
Max rounds: 8
```

### 10.1 整体结果

| 指标 | Zero-shot | Retrieval few-shot |
|---|---:|---:|
| Root-cause Accuracy | 87.5% | 90.0% |
| Repair Strategy Accuracy | 7.5% | 62.5% |
| Joint Success | 7.5% | 62.5% |
| Process Success | 80.0% | 80.0% |
| Overall Success | 5.0% | 50.0% |
| Expected Metric Recovery | 6.8% | 55.5% |
| Fraud Recall Recovery | 6.7% | 55.5% |
| Amount Recall Recovery | 6.5% | 49.5% |
| Rule Robustness | 3.8% | 46.2% |
| Safe Deployment Rate | 5.0% | 50.0% |
| Avg Time-to-Mitigation | 22.2h | 13.1h |

核心结论：

```text
Zero-shot 已经能较好识别根因，但不会稳定选择生产修复策略。
Retrieval few-shot 主要提升的是修复决策能力，而不是根因识别能力。
```

### 10.2 Retrieval few-shot 分类别结果

| 类别 | Task Success | Process Success | Overall | Metric Recovery | Fraud Recall | Safe Deploy | 解读 |
|---|---:|---:|---:|---:|---:|---:|---|
| A_DataIntegrity | 100.0% | 100.0% | 100.0% | 86.1% | 86.1% | 100.0% | 数据链路故障最稳定 |
| B_DistributionShift | 50.0% | 100.0% | 50.0% | 47.5% | 47.5% | 50.0% | 阈值/客群迁移较好，重训决策偏弱 |
| C_AdversarialDrift | 83.3% | 100.0% | 83.3% | 70.9% | 70.9% | 83.3% | 对抗漂移和规则更新表现较好 |
| D_FeedbackLoop | 37.5% | 100.0% | 37.5% | 33.6% | 33.6% | 37.5% | 标签延迟和规则交互仍弱 |
| E_AgentToolUse | 62.5% | 0.0% | 0.0% | 54.8% | 54.8% | 0.0% | 答案部分正确，但流程不合规，不能安全上线 |

当前暴露出的主要问题：

- D 类反馈闭环难，因为正确动作常常是“不要修模型”，而是等待标签成熟或修正规则链路；
- B 类中 `model_capacity_issue` 较弱，Agent 不太敢推荐 `full_retraining`；
- E 类说明“答案正确”不等于“生产可上线”，工具流程、replay、预算仍需强化；
- 规则更新的 replay / 抗绕过验证还不够稳定。

---

## 11. 运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

Mock 模式运行，无需 API：

```bash
LLM_MODEL=mock python3 -m experiments.evaluate_diagnosis \
  --modes baseline retrieval \
  --max-rounds 8 \
  --output-prefix diagnosis_mock
```

使用 OpenAI-compatible API：

```bash
export OPENAI_API_KEY="your_api_key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o-mini"
export LLM_TEMPERATURE=0.2

python3 -m experiments.evaluate_diagnosis \
  --modes baseline retrieval \
  --max-rounds 8 \
  --output-prefix diagnosis_gpt4omini
```

不重新请求 LLM，直接用已有 trajectory memory 重新生成报告：

```bash
LLM_MODEL=gpt-4o-mini python3 -m experiments.evaluate_diagnosis \
  --modes baseline retrieval \
  --from-memory \
  --output-prefix diagnosis_from_memory
```

构造 DPO-style preference 数据：

```bash
python3 -m experiments.build_diagnosis_dpo_data
```

---

## 12. 重要文件

```text
data/production_diagnosis/eval_events.json
data/production_diagnosis/seed_diagnosis_trajectories.json

src/production_diagnosis/state.py
src/production_diagnosis/policy.py
src/production_diagnosis/orchestrator.py
src/production_diagnosis/rule_stream.py
src/production_diagnosis/tool_lab.py
src/production_diagnosis/memory.py

experiments/evaluate_diagnosis.py
experiments/build_diagnosis_dpo_data.py

docs/production_diagnosis.md
```

最新报告：

```text
logs/diagnosis_fraud_metrics_gpt4omini_gpt-4o-mini_baseline.md
logs/diagnosis_fraud_metrics_gpt4omini_gpt-4o-mini_retrieval.md
```

---

## 13. DPO 数据构造方向

当前项目是 DPO-ready，但最新主结果主要来自 zero-shot vs retrieval few-shot。DPO 不应该训练单步答案，而应该训练完整专家轨迹偏好。

示例：

```text
State:
label_maturity = 0.34
pending_review_ratio 高
短期 precision 下降

Chosen trajectory:
analyze_segment_drop
-> check_label_maturity
-> terminate(defer_until_label_mature)

Rejected trajectory:
analyze_segment_drop
-> compute_feature_psi
-> recommend_partial_retraining
-> terminate(partial_retraining)
```

偏好原则：

```text
安全上线 > 误伤控制 > 召回/金额恢复 > 自动化率
```

应该构造的 rejected 轨迹包括：

- 最终答案对，但漏 replay；
- 标签未成熟时直接重训；
- 把规则交互污染误判成阈值失准；
- 通过排除困难 segment 提升指标；
- 不必要的 full retraining；
- 不确定时强行自动修复，而不是 human review。

---

## 14. 项目边界

这是一个研究型原型，不是已经上线的生产系统。

- 评测集是 synthetic benchmark，但按照反欺诈生产常见故障模式构造；
- Tool layer 是确定性模拟工具，尚未连接真实 SQL / SHAP / Graph / Replay 服务；
- DPO 对齐是后续方向，当前主结果不是完整 DPO 训练结果；
- 部分业务指标，例如 time-to-mitigation 和 recovery，是 deterministic estimate；
- 当前 retrieval 使用 TF-IDF，生产版本应升级为 hybrid dense retrieval。

准确定位：

```text
这个项目验证的是反欺诈模型衰退诊断 Agent 的架构和评测体系，
不是一个完整可直接上线的生产系统。
```

---

## 15. 后续计划

1. 将模拟工具替换为真实 SQL、数据质量、SHAP、图分析和 replay 服务；
2. 将 TF-IDF retrieval 升级为 embedding + metadata filter + rerank；
3. 构造 accepted / rejected 专家轨迹，进行 SFT/DPO；
4. 强化 RuleStream，覆盖标签延迟、规则交互、reward hacking、replay；
5. 将评测集从 40 条扩展到 80-120 条；
6. 引入真实专家审核标签，形成 trajectory acceptance 闭环。

---

## 16. License

Demo / research prototype。项目数据为合成数据，不包含真实用户信息。

