# 对比评测报告 — base model: `mock`

评测时间: 2026-07-20 10:55:30

## 汇总对比

| Mode     |   N | Strict Acc   | Lenient Acc   |   Rounds | Avg Time   |   #Rules | Rule Recall   | Rule Precision   | Rule FP   |
|----------|-----|--------------|---------------|----------|------------|----------|---------------|------------------|-----------|
| baseline |   6 | 100.0%       | 100.0%        |        5 | 0.0s       |        6 | 32.6%         | 100.0%           | 0.00%     |
| few_shot |   6 | 100.0%       | 100.0%        |        5 | 0.0s       |        6 | 32.6%         | 100.0%           | 0.00%     |

## Mode 说明

- **baseline**: 无 case few-shot + 无 alignment 偏好(纯硬护栏 + 语义级动作空间)
- **few_shot**: 有 case few-shot + 无 alignment 偏好(检索历史成功轨迹作示范)
