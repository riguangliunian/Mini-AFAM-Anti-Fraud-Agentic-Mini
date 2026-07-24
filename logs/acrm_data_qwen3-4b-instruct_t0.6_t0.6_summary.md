# 对比评测报告 — base model: `qwen3-4b-instruct_t0.6_t0.6`

评测时间: 2026-07-20 14:34:41

## 汇总对比

| Mode     |   N | Strict Acc   | Lenient Acc   |   Rounds | Avg Time   |   #Rules | Rule Recall   | Rule Precision   | Rule FP   |
|----------|-----|--------------|---------------|----------|------------|----------|---------------|------------------|-----------|
| few_shot |  34 | 35.3%        | 70.6%         |      4.9 | 74.0s      |       34 | 75.7%         | 98.8%            | 0.04%     |

## Mode 说明

- **few_shot**: 有 case few-shot + 无 alignment 偏好(检索历史成功轨迹作示范)
