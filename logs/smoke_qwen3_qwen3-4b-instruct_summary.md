# 对比评测报告 — base model: `qwen3-4b-instruct`

评测时间: 2026-07-20 11:45:59

## 汇总对比

| Mode     |   N | Strict Acc   | Lenient Acc   |   Rounds | Avg Time   |   #Rules | Rule Recall   | Rule Precision   | Rule FP   |
|----------|-----|--------------|---------------|----------|------------|----------|---------------|------------------|-----------|
| baseline |   2 | 100.0%       | 100.0%        |        5 | 52.3s      |        2 | 52.6%         | 100.0%           | 0.00%     |

## Mode 说明

- **baseline**: 无 case few-shot + 无 alignment 偏好(纯硬护栏 + 语义级动作空间)
