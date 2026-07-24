# 对比评测报告 — base model: `qwen3-4b-instruct`

评测时间: 2026-07-20 12:55:04

## 汇总对比

| Mode     |   N | Strict Acc   | Lenient Acc   |   Rounds | Avg Time   |   #Rules | Rule Recall   | Rule Precision   | Rule FP   |
|----------|-----|--------------|---------------|----------|------------|----------|---------------|------------------|-----------|
| baseline |  34 | 41.2%        | 41.2%         |        5 | 53.8s      |       33 | 75.0%         | 98.7%            | 0.04%     |
| few_shot |  34 | 47.1%        | 91.2%         |        5 | 63.8s      |       34 | 75.7%         | 98.8%            | 0.04%     |

## Mode 说明

- **baseline**: 无 case few-shot + 无 alignment 偏好(纯硬护栏 + 语义级动作空间)
- **few_shot**: 有 case few-shot + 无 alignment 偏好(检索历史成功轨迹作示范)
