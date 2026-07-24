# Design Decisions

一份"为什么这么做"的说明,分享/答辩时可以拿来直接讲。

## 1. 为什么选团伙调查(方向 B),而不是规则维护(方向 A)

**方向 A(规则维护)**:和 ACRM 直接对标(都是维护型 Agent)。
**方向 B(团伙调查)**:生成型 Agent,和 ACRM 是"同架构但不同问题"。

选 B 的原因:
- 图密集,能突出反欺诈独特性
- Demo 视觉效果强(图扩展、社区发现)
- 能自然引出"标签成熟度、对抗测试"等 ACRM 完全没有的机制

**代价**:需要在分享时诚实说明"这是不同性质的问题",不能声称"和 ACRM 一样"。

## 2. 为什么图不进 LLM context

**核心问题**:LLM 读不懂邻接结构,而且塞不下。

**方案**:
- Python 处理图(NetworkX)
- 输出**自然语言诊断报告** + **图指纹**
- LLM 只读报告

**代价**:诊断报告的表达能力有上限,复杂图 pattern 可能丢失。
**规避**:关键统计量(size/density/community_count)转成 bucket,进指纹。

## 3. 为什么动作是"语义级"

LLM 生成 `{"action_type": "expand_neighbors", "params": {"hop": 1, "edge_type": "device_id"}}` 而不是原始 Cypher 查询。

**原因**:
- LLM 擅长选动作类型,不擅长写正确的图查询
- 语义动作有 10 个模板可枚举,便于 Rule Stream 校验
- 底层实现可以改(比如从 NetworkX 换 Neo4j)不影响 Agent

## 4. 为什么用 Mock LLM 做默认

**原因**:
- 无 API key 也能跑
- 决策论确定性,便于消融
- Demo 现场不会因为网络抖动挂

**代价**:偏好对齐效果不真实,消融实验里 alignment 差异不明显。
**规避**:切换到真实 API(`LLM_MODEL=gpt-4o-mini`)时可以看到显著差异。

## 5. 为什么 DPO 用 prompt engineering 模拟

**原因**:
- 一周训不出真 DPO(数据 + 训练时间)
- Prompt 里写清偏好("prefer precise multi-condition rules over broad ones")能达到 70% 效果

**规避真实项目的路径**:
1. Trajectory Memory 里已经有 `label: accepted/rejected` 字段
2. 攒够 500+ 条后可以按 ACRM Section 3.3 构造偏好对
3. 用 LoRA + DPO 微调 open-weight 模型

## 6. 为什么合成数据 1000 条

**原因**:
- 真实数据一周拿不到
- 1000 条足够展示图团伙的结构模式
- NetworkX 内存跑,秒级出结果

**规避**:
- 3 个明显团伙 + 2 个微妙团伙 + 2 个 WiFi 干扰组
- 有真值标签(true_label 字段)可评估

## 7. 为什么加"WiFi 邻居"干扰组

**核心 demo 卖点**:
- 只用结构信号(shared_ip)会把这组好用户误伤
- Rule Stream 的 STRUCTURE_ONLY_RULE 护栏必须组合属性信号才允许
- alert_005 用来演示"看起来像团伙但不是"的分辨

## 8. 为什么标签成熟度作为一等字段

ACRM 没有这个概念(KS 是即时可算的),但反欺诈里:
- Chargeback 30-60 天才回来
- 早期只有代理标签(FPD、规则命中、人工标记)

**实现**:
- 数据生成时给每个用户随机成熟度
- State 里累积平均值
- Rule Stream 拦"低成熟度 + 高置信度"组合

## 9. 为什么加 Adversarial Prober

ACRM 完全没有,但反欺诈是**对抗游戏**:
- 每次上规则,黑产都会研究并反制
- 内部先"红队自测"能大幅降低外部绕过率

**实现**:5 种典型绕过策略枚举,看规则是否单一维度可绕过。真实项目可用 LLM 生成更复杂的绕过场景。

## 10. 为什么保留"Rule Stream 拒绝重试"循环

对应 ACRM 的 Generate-then-Validate。**这是所有 Agent 系统里最容易被砍掉但最重要的机制**:
- LLM 会自由发挥,规则会限制它
- 两者配合而不是替代
- 错误信息带回 prompt,让 LLM 学会遵守

一周项目里我们只做了 2 次重试,真实项目应加"重试模式"—— 三次都失败自动降级为 escalate。

## 11. 一些没做的(留给下一版)

- **真 DPO 训练**:需要攒够 500+ 条真实轨迹
- **图 embedding 检索**:用 GraphSAGE 而不是简单指纹
- **实时 shadow 流**:demo 是离线 replay
- **前端可视化**:目前只有 terminal 输出
- **规则冲突检测**:两条新规则相互覆盖时的处理
- **合规审计导出**:生成人工审核报告的 PDF/HTML

## 12. Demo 叙事(3 段论)

**Segment 1 — 定位差异**
"ACRM 是模型刷新,是维护性问题。我们做的是团伙调查,是生成性问题。共用架构,不同本质。"

**Segment 2 — 3 个决定性演示**
1. alert_000(明显团伙):5 轮完整走完 expand→rule→shadow→adversarial→terminate
2. alert_003(微妙团伙,标签不成熟):触发 LABEL_MATURITY_GUARD,降级为 escalate
3. alert_005(WiFi 误报):Retrieval 匹配 seed_002,识别为 not_fraud

**Segment 3 — Ablation 数据**
"Full AFAM 有 17% escalate rate — 这不是失败,是识别出了不确定案例。No-Rules 版本对所有案例硬答,包括本该 escalate 的。"
