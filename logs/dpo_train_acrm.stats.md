# ACRM-style DPO Dataset — Statistics

**Total pairs**: 121

## Source breakdown

| Source | Count | % | ACRM equivalent |
|---|---|---|---|
| `accepted_vs_rejected` | 87 | 71.9% | ① Accepted vs Rejected (ACRM: 55%) |
| `accepted_vs_accepted` | 26 | 21.5% | ② Accepted vs Accepted (ACRM: 35%, 精髓) |
| `cross_alert_accepted_vs_rejected` | 8 | 6.6% | 跨场景 A vs R (ACRM: cosine>0.75 匹配) |

## Accepted-vs-Accepted 复合分数差异分布

- 样本数: 26
- 差异均值: 0.432
- 差异范围: [0.080, 1.230]

**权重设定**: α_verdict=1.0, α_conf=0.5, α_recall=0.6, β_fp=3.0, γ_esc=1.5, δ_rounds=0.3

## Per-alert 覆盖

- 覆盖 alert 数: 34
- 同时有 accepted + rejected 轨迹的 alert: 20(可造 A-vs-R)
- accepted 轨迹 ≥ 2 的 alert: 31(可造 A-vs-A)