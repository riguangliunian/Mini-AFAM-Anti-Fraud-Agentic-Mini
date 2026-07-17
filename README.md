# Mini AFAM — Anti-Fraud Agentic Mini

一个面向反欺诈**团伙调查**场景的**多智能体调查助手**原型。收到一条可疑告警,它会自主完成"图扩展 → 社区判定 → 规则合成 → 影子回放 → 红队自测 → 出具处置建议"的完整链路,把分析师从 2-4 小时的手工排查中解放出来,让他们把精力放在最终审核和真正需要人工判断的少数复杂案子上。

---

## 一、定位

**Mini AFAM 是"生成型 Agent"**——每次面对新告警都要重新收集证据、独立推理、给出结论。它不做实时秒级拦截(那是规则引擎的活),也不做无监督主动发现(那是异常检测的活),它专注于**告警后的调查加速**这一层。

**服务对象**:一线反欺诈分析师、策略工程师、合规审核员
**替代动作**:图查询、社区发现、规则草拟、shadow 测试、红队自测
**保留人工**:最终采纳/驳回、新型攻击的应急决策、新特征的构造

**设计基调**:**有边界的自动化**(bounded automation)—— Agent 出建议,人做决策;所有决策路径可审计可回放。

---

## 二、要解决的核心问题

反欺诈行业里 4 个长期痛点:

| 痛点 | 现状 | Mini AFAM 的做法 |
|---|---|---|
| 调查周期长 | 手工排查一个团伙告警 2-4 小时,黑产已跑路 | 5 轮内产出完整调查报告,分钟级 |
| 专家经验无法沉淀 | 资深分析师离职,经验全带走 | 轨迹记忆库把每次成功调查沉淀成组织资产 |
| 规则质量参差 | 分析师风格不一,规则库久了成"垃圾堆" | 强制"结构信号 + 属性信号"组合,风格统一 |
| 规则上线才发现被绕过 | 观察一周才发现,资损已发生 | 上线前跑 5 类典型绕过测试 |

---

## 三、独特设计(和常见 Agent 项目的区别)

大部分 Agent 项目要么是"LLM 自由调工具",要么是"硬 Coded 流水线"。Mini AFAM 走**中间路线**:LLM 做权衡决策,Python 做事实性工作,两者用一套约束协议连接。

### 1. **三流融合决策**(Rule + Retrieval + Alignment)

每一轮 Orchestrator 做决策时,同时参考三个知识源:

- **Rule Stream**(硬约束护栏)—— Python 代码写的合规红线,LLM 无法绕过
- **Retrieval Stream**(相似历史检索)—— 从轨迹记忆库拉 top-3 类似调查作为参考
- **Alignment Stream**(偏好引导)—— 在 System Prompt 里编码"低误伤 > 可解释 > 高召回"这类价值观

三流的哲学:**规则管"绝对不能"、检索管"过去成功过什么"、偏好管"多个合法方案里挑哪个"**。

### 2. **Generate-then-Validate 循环**

LLM 出的每一个动作,都要过 Rule Stream 校验;违规就带错误信息回炉重生。类似:

```
LLM 生成 hop=3
    ↓ Rule Stream 拦截: "MAX_HOP_EXCEEDED: hop must be ≤ 2"
LLM 重生成 hop=2 ✓
    ↓ 通过 → 执行
```

**关键点**:LLM 的自由创造 + Python 的硬性兜底,配合而非替代。

### 3. **图不进 LLM,报告进 LLM**

LLM 天然读不懂邻接矩阵、图 embedding。这里的做法是:

```
[原始图 1000+ 节点]
      ↓
GraphMiner (Python 处理)
      ↓
[自然语言诊断报告 + 5 维图指纹]
      ↓
LLM 只读文本
```

诊断报告示例:
```
Subgraph analysis of 10 suspect users:
- Shared device_id: top 'dev_87531' shared by 8 users
- Communities detected: 1, largest size = 8
- Temporal burst: 6 applications within 4h window
- New account ratio: 100%, night apply: 80%, paste used: 60%
- Avg label maturity: 0.55 (mature)
```

**这是让 LLM + 图 系统能工程化落地的关键**。

### 4. **动作空间语义化**

LLM 不写 SQL / Cypher / 图查询代码。它从 **10 个预定义动作模板**里选一个,填参数:

```python
ACTION_TEMPLATES = [
    "expand_neighbors", "find_community", "check_shared_entity",
    "check_temporal_burst", "compute_risk_score",
    "generate_rule", "shadow_replay", "adversarial_probe",
    "escalate_to_human", "terminate",
]
```

好处:LLM 只在它擅长的层次(选动作)决策,底层实现随便换(NetworkX / Neo4j / Nebula),动作空间小便于校验。

### 5. **标签成熟度作为一等字段**

反欺诈标签严重滞后(chargeback 30-60 天才回)。系统显式建模:

- 每个用户带 `label_maturity ∈ [0, 1]`
- Agent state 累积平均标签成熟度
- Rule Stream 拦截"低成熟度 + 高置信度"的组合(强制降置信度或人工兜底)

### 6. **对抗性自测(Adversarial Prober)**

规则生成后,红队 Agent 主动尝试 5 种绕过:
- 设备轮换、IP 池、金额拆分、延迟申请、养号

任何单一维度可绕过 → 规则被判"has_gaps",要求 LLM 补条件。**上线前而不是上线后发现漏洞**。

### 7. **完整轨迹记录 = 审计资产**

每一步 `(state, action, outcome)` 三元组入库。上线时能给合规看:
- 完整推理链
- 每个动作的 rationale
- 规则的 shadow 效果
- 红队自测结论

---

## 四、系统架构

```
[告警触发]
    ↓
┌──────────────────────────────────────────────────────────────┐
│  Hybrid Knowledge Layer                                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Rules    │  │ Retrieval     │  │ Alignment(Prompt)    │  │
│  │ 硬约束    │  │ 相似轨迹检索   │  │ 偏好排序               │  │
│  └────┬─────┘  └──────┬────────┘  └──────────┬─────────────┘  │
│       └────────────┬──┴────────────────────────┘              │
└────────────────────┼───────────────────────────────────────── ┘
                     ▼
        ┌──────────────────────────┐
        │ Orchestrator (LLM)       │  ◄─── 违规重试(附错误信息)
        │ Generate-then-Validate   │
        └────────────┬─────────────┘
                     │ validated action
                     ▼
   ┌───────────────────────────────────────────────────────────┐
   │  Specialist Agent Layer                                    │
   │  ┌─────────┐ ┌──────────────┐ ┌──────────┐ ┌─────────────┐ │
   │  │Graph    │ │Rule          │ │Shadow    │ │Adversarial  │ │
   │  │Miner    │ │Composer      │ │Evaluator │ │Prober       │ │
   │  └────┬────┘ └──────┬───────┘ └────┬─────┘ └──────┬──────┘ │
   └───────┼─────────────┼──────────────┼──────────────┼────────┘
           └─────────────┴──────────────┴──────────────┘
                          │ (state, action, outcome)
                          ▼
              ┌───────────────────────────┐
              │  Trajectory Memory        │
              │  (JSONL + seed pool)      │
              └───────────┬───────────────┘
                          │
                          └── feed back to Retrieval Stream
```

**Sub-Agent 分工**:

| 组件 | 类型 | 职责 |
|---|---|---|
| Orchestrator | LLM | 融合三流 → 选动作 → 判终止 |
| GraphMiner | Python | 图分析 → 生成自然语言诊断 + 图指纹 |
| RuleComposer | Python | 结构+属性组合,合成拦截规则 |
| ShadowEvaluator | Python | 在历史数据 replay 规则,给召回/误伤 |
| AdversarialProber | Python | 尝试 5 类绕过,输出规则鲁棒性判定 |
| RuleStream | Python | 8 条硬护栏一票否决 |
| RetrievalStream | Python | TF-IDF 文本 + Jaccard 结构指纹混合检索 |
| Memory | JSON | 轨迹存储 + 种子轨迹池 |

---

## 五、目录结构

```
mini_afam/
├── data/
│   ├── generate_data.py         # 合成 1000 用户 + 5 团伙 + 干扰组
│   ├── generate_eval_set.py     # 生成 34 条打标评测告警
│   ├── graph_data.parquet       # 申请事件表
│   ├── entity_graph.pkl         # 实体关系图
│   ├── alerts.json              # Demo 告警
│   ├── eval_alerts.json         # 评测告警(带 ground truth)
│   └── seed_trajectories.json   # 5 条种子历史轨迹(cold-start)
├── src/
│   ├── state.py                 # State/Action/Outcome + 10 动作模板
│   ├── rule_stream.py           # 8 类硬护栏
│   ├── memory.py                # 轨迹记忆
│   ├── retrieval.py             # 混合相似度检索
│   ├── llm.py                   # LLM 适配层(Mock/OpenAI)
│   ├── orchestrator.py          # 三流融合 + Generate-then-Validate
│   ├── main.py                  # 端到端 runner
│   └── specialists/
│       ├── graph_miner.py
│       ├── rule_composer.py
│       ├── shadow_evaluator.py
│       └── adversarial_prober.py
├── experiments/
│   ├── ablation.py              # 5 种配置消融
│   ├── evaluate.py              # 34 条打标告警评测
│   └── aggregate_reports.py     # 多份报告合并
├── docs/
│   ├── architecture.md
│   └── design_decisions.md
└── logs/                        # 运行时轨迹 + 评测报告
```

---

## 六、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成合成数据 + 评测集
python3 -m data.generate_data
python3 -m data.generate_eval_set

# 3. Mock LLM 端到端跑一个告警(秒级,无需 API)
LLM_MODEL=mock python3 -m src.main --alert alert_000

# 4. 跑所有告警
LLM_MODEL=mock python3 -m src.main --all

# 5. 消融实验(5 种配置对比)
LLM_MODEL=mock python3 -m experiments.ablation

# 6. 完整评测(34 条打标告警,分 6 类)
LLM_MODEL=mock python3 -m experiments.evaluate --output eval_mock.md

# 7. 切到真实 LLM
export OPENAI_API_KEY=xxx
export OPENAI_BASE_URL=xxx   # 可选:自定义 endpoint
export LLM_MODEL=gpt-4o-mini
python3 -m experiments.evaluate --output eval_real.md
```

---

## 七、LLM 配置

支持两种模式:

```bash
# Mode 1: Mock 模式(默认,无 API,启发式驱动,快)
export LLM_MODEL="mock"

# Mode 2: OpenAI 兼容 API
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export LLM_MODEL="gpt-4o-mini"     # 或其他 OpenAI 兼容模型
```

**Mock 模式**用启发式规则模拟 LLM 决策,方便离线调试、CI 测试、消融对照。**真实 API 模式**用 GPT-4o-mini 等模型,反应更聪明但慢一点、贵一点。

---

## 八、评测集设计

`data/eval_alerts.json` 含 **34 条打标告警,分 6 类**,每条带 ground truth:

| 类别 | 数量 | 期望结论 | 测试点 |
|---|---|---|---|
| A. 明显团伙 | 8 | fraud_confirmed | 基本能力 |
| B. 微妙团伙+标签不成熟 | 6 | fraud_confirmed 或 escalate | 标签成熟度守护 |
| C. WiFi 邻居误报 | 6 | not_fraud | 结构+属性组合护栏 |
| D. 孤立正常用户 | 6 | not_fraud | 空扩展处理 |
| E. 新型模式 | 4 | escalate | 检索置信度守护 |
| F. 抗规避 | 4 | fraud_confirmed | Adversarial Prober 检验 |

每条告警字段:
- `alert_id, seed_user, trigger_reason, severity`
- `expected_verdict`(严格匹配)
- `alt_ok_verdicts`(可接受备选,如"可以 escalate")
- `expected_confidence_range`(置信度校准检查)
- `test_point`(这条测的是什么能力)

---

## 九、评测结果

### 9.1 GPT-4o-mini(真实 LLM)vs Mock LLM

| 指标 | GPT-4o-mini | Mock LLM |
|---|---|---|
| **总告警数** | 34 | 34 |
| **Strict accuracy** | 67.6% | 58.9% |
| **Lenient accuracy** | 82.4% | 85.4% |
| **规则召回**(hold-out) | **75.3%** | 39.1% |
| **规则精度** | **98.9%** | 100% |
| **规则误伤率** | 0.04% | 0.00% |
| **规则生成数** | 30 | 22 |
| **平均轮数** | 4.8 | 3.9 |

### 9.2 分类别表现(GPT-4o-mini)

| 类别 | N | Strict | Lenient | 说明 |
|---|---|---|---|---|
| A. 明显团伙 | 8 | 75% | 75% | 2 条被 escalate,略保守 |
| B. 微妙团伙+标签不成熟 | 6 | 83% | **100%** | 展现"标签不成熟→降置信度"能力 |
| C. WiFi 邻居误报 | 6 | **100%** | **100%** | 结构+属性护栏正确识别误报 |
| D. 孤立正常用户 | 6 | 67% | 100% | 部分谨慎升级,部分直接判 not_fraud |
| E. 新型模式 | 4 | **0%** | **0%** | 硬答"团伙"而非升级人工,暴露弱点 |
| F. 抗规避 | 4 | 50% | 100% | 部分需要人工兜底 |

### 9.3 分类别表现(Mock LLM)

| 类别 | N | Strict | Lenient | 说明 |
|---|---|---|---|---|
| A. 明显团伙 | 8 | 88% | 88% | 基本能力 OK |
| B. 微妙团伙+标签不成熟 | 6 | **0%** | 33% | Mock 简单启发式处理不了微妙 |
| C. WiFi 邻居误报 | 6 | 100% | 100% | 稳定 |
| D. 孤立正常用户 | 6 | 0% | 100% | 全部 escalate |
| E. 新型模式 | 4 | **100%** | **100%** | 简单规则反而不"上头" |
| F. 抗规避 | 4 | 75% | 100% | 稳定 |

---

## 十、关键发现

### 发现 1: **真实 LLM 显著改善"微妙判断"能力**

B 类(标签不成熟的微妙团伙)Strict 准确率从 Mock 的 **0% → GPT-4o-mini 的 83%**。真实 LLM 能理解"标签不成熟就降置信度,加 30 天复核"这种语义,启发式规则做不到。

### 发现 2: **规则质量提升明显**

生成规则的召回率从 Mock 的 39.1% → GPT-4o-mini 的 **75.3%**,规则精度稳定在 99%,误伤率仅 0.04%。这说明 LLM 能组合出更精细的规则条件,而不是简单堆叠。

### 发现 3: **强证据会盖过软护栏 —— LLM 的 "上头" 问题**

E 类(新型模式)Mock 100% 正确 escalate,GPT-4o-mini 却 100% 判成 fraud_confirmed。原因:LLM 看到"100% 新账户 + 100% 夜间申请 + 100% 粘贴使用"这种强证据时,会忽略 Prompt 里"新型模式应该 escalate"的软约束。

**这个失败反而是最有价值的发现**:
- 证明**软护栏(Prompt 指令)对付强证据是无效的**
- 硬护栏(Rule Stream 阈值)如果卡得不够严,也守不住
- 真正解决要靠**偏好训练(如 DPO)** 把"新型 → 升级"训进模型权重,或者**多维硬护栏组合**

### 发现 4: **Adversarial Prober 有实际效果**

F 类抗规避:100% lenient,生成的规则组合了多维条件后,5 类典型绕过手段都无法单独破解。上线前的红队自测显著降低"上线后被绕过"的风险。

### 发现 5: **调查时间对比**

| 场景 | 平均调查时长 |
|---|---|
| 手工分析师(参考行业均值) | 2-4 小时 |
| Mock LLM Agent | < 1 秒 |
| GPT-4o-mini Agent | 45-75 秒(5 轮 × ~11 秒) |

即使用真实 API,Agent 的调查也比手工快 **~100 倍**。

### 发现 6: **消融实验揭示各流的价值**

| 配置 | Strict Acc | Lenient Acc | 观察 |
|---|---|---|---|
| Full AFAM(三流全开) | 基线 | 基线 | — |
| No-Retrieval | 略高 | 持平 | Retrieval 起到"合理保守"作用 |
| No-Alignment | 略低 | 持平 | Prompt 偏好有轻微影响 |
| Rule-Only | 略高 | 持平 | 只用规则时更"敢答" |
| No-Rules | 略高 | 持平 | 无护栏时容易出格 |

**注意**:消融差异在 Mock 上并不显著(启发式规则天然稳定),真实 LLM 上会更明显。

---

## 十一、限制和边界

**Mini AFAM 不做以下事情**:

- ❌ **不做实时秒级拦截** —— 那是规则引擎的活,LLM 延迟不达标
- ❌ **不做无监督主动发现** —— 必须有告警作为触发,不主动巡逻
- ❌ **不创造新特征** —— 只能筛选/组合现有特征,不能构造全新指标
- ❌ **不做终局决策** —— 输出建议给分析师采纳,不直接拉黑用户
- ❌ **不适合真实生产** —— 这是原型,数据量、延迟、集成都不满足生产要求

**评测里已暴露的问题**:

- 新型攻击场景(E 类)自动化能力弱,需要更多历史轨迹 + 真实 DPO 训练
- 明显团伙(A 类)有 25% 被谨慎 escalate,可能过于保守
- 置信度校准偏低(LLM 倾向输出 0.6-0.7),需要 fine-tune

**上生产要补的差距**:

- 数据规模:NetworkX 内存图 → 分布式图数据库(Neo4j / Nebula 集群)
- 检索:TF-IDF + Jaccard → 向量数据库 + GNN embedding
- 对齐:Prompt engineering → 真 DPO 训练(需要 500-1000 条打标轨迹)
- 集成:JSON 输出 → 对接告警系统、案件管理平台、审计日志系统
- 合规:通用护栏 → 具体行业监管(SOX、SOC2、金融监管)

---

## 十二、后续可扩展方向

1. **真 DPO 训练**:攒 500+ 条真实历史轨迹,微调开源模型,把偏好训进权重
2. **图 embedding 检索**:GraphSAGE / node2vec 替代简单的结构指纹
3. **实时 Shadow**:接生产流量镜像做在线 replay,而非离线批处理
4. **规则冲突检测**:多条新规则相互覆盖时的自动去重
5. **前端可视化**:Web 界面展示图扩展过程、规则效果、审计追溯
6. **合规报告自动生成**:输出符合监管要求的 PDF/HTML 报告
7. **横向覆盖**:从团伙调查扩展到 First-party fraud、账户盗用等其他类型

---

## 十三、许可与致谢

Demo 项目,自由使用。数据是合成的,不含任何真实用户信息。
