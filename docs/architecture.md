# Mini AFAM 架构说明

## 一、整体架构图

```
┌────────────────────────────────────────────────────────────────┐
│                        触发:告警事件                          │
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────────┐
│              Hybrid Knowledge Layer(三流)                     │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────────┐  │
│  │  Rules   │   │  Retrieval   │   │  Alignment (Prompt-simulated)│
│  │  硬约束  │   │  相似轨迹     │   │  偏好排序                 │  │
│  └────┬─────┘   └──────┬───────┘   └──────────┬─────────────┘  │
│       │                 │                     │                 │
│       └────────┬────────┴─────────────────────┘                 │
└────────────────┼────────────────────────────────────────────────┘
                 ▼
    ┌───────────────────────────┐
    │  Orchestrator (LLM)       │
    │  Generate-then-Validate   │◄──── Reject with error msg
    └────────────┬──────────────┘
                 │  validated action
                 ▼
    ┌────────────────────────────────────────────────────────────┐
    │             Specialist Agent Layer                          │
    │  ┌──────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────┐│
    │  │  Graph   │ │    Rule     │ │   Shadow     │ │Adversarial││
    │  │  Miner   │ │  Composer   │ │  Evaluator   │ │  Prober   ││
    │  └────┬─────┘ └──────┬──────┘ └──────┬───────┘ └────┬─────┘│
    └───────┼──────────────┼───────────────┼──────────────┼──────┘
            └──────────────┴───────────────┴──────────────┘
                                │  (state, action, outcome)
                                ▼
                    ┌───────────────────────┐
                    │  Trajectory Memory    │
                    │  (JSONL + seed pool)  │
                    └───────────┬───────────┘
                                │
                                └──── feed back to Retrieval
```

## 二、关键组件说明

### 2.1 Orchestrator(`src/orchestrator.py`)

- **模型**:任意 LLM(默认 mock,可切 OpenAI/Anthropic)
- **每轮职责**:融合三流 → 生成候选 → 规则校验 → 派 Specialist → 更新 state
- **循环终止**:`terminate` / `escalate_to_human` / 超过 `max_rounds`

### 2.2 Rule Stream(`src/rule_stream.py`)

反欺诈场景下的硬约束护栏,与 ACRM(PSI/KS 稳定性)完全不同:

| 护栏 | 阈值 | 拒绝的原因 |
|---|---|---|
| MAX_GRAPH_HOP | 2 | 超过 2 跳延迟 > 100ms,在线不可用 |
| MIN_RULE_COVERAGE | 3 | 单规则覆盖太少可能过拟合个案 |
| STRUCTURE_ONLY_RULE | / | 规则只有结构信号(如 shared_ip)会误伤 WiFi 邻居 |
| LABEL_MATURITY_GUARD | maturity ≥ 0.5 | 标签未成熟时不允许高置信度定案 |
| NOVEL_PATTERN_GUARD | retrieval_conf ≥ 0.55 | 新型攻击必须走人工 |
| PRIVACY_GUARD | / | 二跳 contact 扩展需要授权 |

### 2.3 Retrieval Stream(`src/retrieval.py`)

- 混合相似度:**0.4 × TF-IDF 文本相似 + 0.6 × 图指纹 Jaccard**
- 图指纹字段:`size_bucket / community_count_bucket / burst / shared_entity_types / new_account_high`
- 反欺诈里图结构 > 文本描述,所以指纹占大头

### 2.4 Alignment Stream(prompt-simulated,`src/orchestrator.py` 的 SYSTEM_PROMPT)

一周项目里,DPO 训练要几百条真实轨迹 + 数小时训练,不现实。**用 prompt engineering 模拟**:

```
Priority order: LOW-FALSE-POSITIVE > EXPLAINABILITY > HIGH-RECALL > SPEED
- Prefer precise multi-condition rules over broad single-condition rules
- Prefer known-safe patterns (retrieved from memory) over novel guesses
- Prefer escalation over overconfident auto-decisions
```

真实项目应把这套偏好写进 ~1000 对偏好数据,用 DPO 微调。

### 2.5 Specialist Agents

| Agent | 是否 LLM | 输入 | 输出 |
|---|---|---|---|
| GraphMiner | ✗(纯 Python) | 可疑用户集 | **自然语言诊断报告** + 图指纹 |
| RuleComposer | ✗ | 诊断报告 | 结构化 Rule 对象 |
| ShadowEvaluator | ✗ | Rule + 历史流量 | 召回/误伤/精度 |
| AdversarialProber | ✗(demo 用规则,真实项目用 LLM) | Rule | 5 类绕过尝试 |

**核心设计**:LLM 只在 Orchestrator 层用,Specialist 都是确定性 Python 逻辑。这样图/图算法完全不进 LLM context,规避了"LLM 读不懂图"的根本问题。

## 三、Generate-then-Validate 循环

对照 ACRM Algorithm 1:

```
for round in 1..max_rounds:
    retrieved   = retrieval.search(state)
    prompt      = build_prompt(state, retrieved, error_feedback)
    for attempt in 1..max_retries+1:
        raw     = llm.chat(prompt)
        action  = parse(raw)
        v       = rule_stream.validate(action, state)
        if v is None:
            break                    # 通过
        error_feedback = f"[{v.rule_name}] {v.message}"
    if action is None:
        traj.verdict = "escalate"; break
    outcome = specialist.execute(action)
    state.update(action, outcome)
    if action is terminate|escalate:
        break
```

## 四、State 结构

```python
@dataclass
class State:
    alert_id: str
    round_num: int
    diagnostic_report: str          # ← LLM 主要读这个
    suspect_set: list[str]          # 当前可疑用户集
    key_metrics: dict               # 数值指标
    label_maturity: float           # 反欺诈独有 [0,1]
    action_history_summary: list    # 已执行动作
    retrieval_confidence: float     # 上一轮检索置信度
```

**关键设计**:图数据本身**不进 State**。GraphMiner 消化图并输出自然语言 `diagnostic_report`,LLM 只读这个报告。

## 五、Trajectory 结构

```python
@dataclass
class Trajectory:
    alert_id: str
    trigger_reason: str
    steps: list[TrajectoryStep]     # (state, action, outcome) 序列
    verdict: str                    # fraud_confirmed / not_fraud / escalate
    final_confidence: float
    total_seconds: float
    label: str                      # accepted / rejected(供 DPO 训练)
```

## 六、差异点对照表(与 ACRM)

| 维度 | ACRM(信贷模型刷新) | Mini AFAM(团伙调查) |
|---|---|---|
| 问题性质 | 维护型 | 生成型 |
| 优化目标 | KS 恢复 + PSI 稳定 | 高召回 + 低误伤 + 可解释 |
| 动作对象 | 模型/数据/超参 | 图查询/规则/证据链 |
| 硬护栏 | PSI < 0.10 | 误伤率 < 0.5%,规则可解释 |
| 图角色 | 无 | 一等公民 |
| 对抗性 | 无(经济周期漂移) | 强(黑产反制) |
| 标签成熟度 | 隐式(KS 直接可算) | 显式建模 |

## 七、Demo 差异点检查清单

- ✅ **图作为一等公民** — GraphMiner 主动选择 1-hop/2-hop、按 edge_type
- ✅ **多层决策流** — 输出 = 规则 + 证据 + 建议,不是单个模型
- ✅ **标签成熟度** — Rule Stream 里 LABEL_MATURITY_GUARD 拦低成熟度的高置信度决策
- ✅ **对抗性** — AdversarialProber 5 类绕过测试
- ✅ **延迟护栏** — MAX_GRAPH_HOP=2 拒绝深度查询
- ✅ **相似度分层触发不同策略** — retrieval_conf < 0.55 强制 escalate
