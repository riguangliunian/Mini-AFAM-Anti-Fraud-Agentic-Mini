# Full-trajectory DPO dataset statistics

论文对应: Appendix E.1-E.5。

- Loaded unique trajectories: 185
- Removed exact duplicates: 0
- Alerts with usable pairs: 19
- Train/held-out alert overlap: 0
- Matching policy: same alert (conservative substitute for embedding cosine > 0.75)
- Limitation: accepted/rejected comes from eval ground truth, not production deployment review
- Paper scale: 3,012 train / 800 held-out pairs; this local corpus cannot reproduce that scale
- Offline composite scores are retained only in meta and never exposed to either completion

## Train

- Pairs: 56
- Alerts: 14
- Accepted vs Rejected: 36
- Accepted vs Accepted: 20
- Avg chosen rounds: 5.00
- Avg chosen characters: 9749
- Chosen verdicts: {'fraud_confirmed': 37, 'not_fraud': 14, 'escalate': 5}
- Chosen pairs containing failed intermediate outcomes: 56

## Held-out

- Pairs: 21
- Alerts: 5
- Accepted vs Rejected: 15
- Accepted vs Accepted: 6
- Avg chosen rounds: 5.00
- Avg chosen characters: 9250
- Chosen verdicts: {'fraud_confirmed': 11, 'not_fraud': 5, 'escalate': 5}
- Chosen pairs containing failed intermediate outcomes: 21
