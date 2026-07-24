# ACRM-style DPO Dataset — Statistics

**Total pairs**: 99

## Source breakdown

| Source | Count | % | ACRM equivalent |
|---|---|---|---|
| `accepted_vs_rejected` | 71 | 71.7% | ① Accepted vs Rejected (ACRM: 55%) |
| `accepted_vs_accepted` | 28 | 28.3% | ② Accepted vs Accepted (ACRM: 35%, 精髓) |

## Accepted-vs-Accepted 复合分数差异分布

- 样本数: 28
- 差异均值: 0.850
- 差异范围: [0.850, 0.850]

**权重设定**: α=1.0, β=3.0, γ=1.5, δ=0.5

## Per-alert 覆盖

- 覆盖 alert 数: 34
- 同时有 accepted + rejected 轨迹的 alert: 19(可造 A-vs-R)
- accepted 轨迹 ≥ 2 的 alert: 31(可造 A-vs-A)