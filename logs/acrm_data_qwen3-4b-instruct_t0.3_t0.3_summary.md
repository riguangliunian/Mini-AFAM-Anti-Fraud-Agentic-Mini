# 对比评测报告 — base model: `qwen3-4b-instruct_t0.3_t0.3`

评测时间: 2026-07-20 13:52:43

## 汇总对比

| Mode     |   N | Strict Acc   | Lenient Acc   |   Rounds | Avg Time   |   #Rules | Rule Recall   | Rule Precision   | Rule FP   |
|----------|-----|--------------|---------------|----------|------------|----------|---------------|------------------|-----------|
| few_shot |  34 | 47.1%        | 88.2%         |        5 | 68.6s      |       34 | 75.6%         | 98.8%            | 0.04%     |

## Mode 说明

- **few_shot**: 有 case few-shot + 无 alignment 偏好(检索历史成功轨迹作示范)
