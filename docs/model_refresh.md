# Fraud GNN Model Refresh Agent

## 研究对象

该模块不让LLM替代GNN判断欺诈，而是让Agent维护已经上线的反欺诈GNN：发现效果下降后，依次诊断、选择实验、训练候选模型并验证是否值得进入Shadow。

## 目录

```text
src/model_refresh/
├── state.py          # RefreshState/Action/Outcome/Trajectory及动作成本
├── orchestrator.py   # Generate-Validate-Execute闭环
├── policy.py         # Mock策略和真实LLM JSON策略
├── rule_stream.py    # 预算、标签、误伤、OOT和Shadow护栏
├── model_lab.py      # 当前模拟GNN环境；真实训练替换点
├── memory.py         # 已验收刷新轨迹与漂移指纹检索
└── main.py           # 单事件/全事件CLI

data/model_refresh/
├── eval_events.json
└── seed_refresh_trajectories.json

experiments/
├── evaluate_refresh.py
└── build_refresh_dpo_data.py
```

## Action空间

- 诊断：分群、节点特征、图结构、标签成熟度、漏判簇、误伤簇；
- 修复：调整训练窗口、成熟标签加权、困难负样本、增加图关系、修复数据管道；
- 训练：`fine_tune_gnn`；
- 验证：时间外测试与Shadow；
- 终止：部署建议、回滚或人工升级。

每个Action都有预算成本。Rule Stream禁止：

- 未诊断和未选择定向修复就盲目重训；
- 低标签成熟度下不做样本加权就训练；
- 没有候选模型就做时间外测试；
- 跳过时间外测试直接Shadow；
- 跳过Shadow或误伤超标直接建议发布；
- 候选模型没有实质收益却替换Champion。

## 运行

```bash
# 单个漂移事件
LLM_MODEL=mock python -m src.model_refresh.main --event refresh_graph_01

# 全量Mock回归
LLM_MODEL=mock python -m experiments.evaluate_refresh \
  --modes baseline retrieval \
  --output-prefix refresh_eval

# 构造决策点级DPO数据
python -m experiments.build_refresh_dpo_data \
  --output logs/refresh_dpo_train.jsonl
```

使用真实基础模型或DPO模型时，沿用项目现有环境变量：

```bash
export LOCAL_MODEL_PATH=/path/to/merged/model
export LLM_MODEL=local
export LLM_TEMPERATURE=0.2
python -m experiments.evaluate_refresh --modes dpo
```

## 接入真实GraphSAGE

当前`SimulatedGNNModelLab`根据事件和修复动作确定性地产生指标，仅用于验证Agent控制逻辑。真实接入时新增`GraphSAGEModelLab`并实现：

```python
class GraphSAGEModelLab:
    def execute(self, action, state, event) -> RefreshOutcome:
        ...
```

其中：

- `fine_tune_gnn`提交真实训练任务并返回候选版本、PR-AUC、固定FPR召回、金额召回、误伤率和GPU小时；
- `run_out_of_time_test`必须使用未来且标签成熟的时间窗口；
- `run_shadow_evaluation`连接Champion-Challenger结果；
- 所有数据版本、模型版本和实验ID写入Outcome，供轨迹审计。

真实实验应按时间切分训练/验证/测试，并用生产基准率数据报告结果。Mock的100%成功率只是单元/流程回归，不能用于论文或简历中的效果声明。
