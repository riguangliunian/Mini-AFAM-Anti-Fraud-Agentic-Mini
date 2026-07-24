"""
Orchestrator:三流融合决策 + Generate-then-Validate。

对应 ACRM 论文 Algorithm 1。
每轮:
  1. Retrieval 拉相似历史轨迹(few-shot)
  2. Rule Stream 组装硬约束提示
  3. Alignment(通过 system prompt 里的偏好描述模拟)
  4. LLM 生成候选动作
  5. Rule Stream 校验;违规 → 附错误信息重生成
  6. 派给 Specialist 执行
  7. 更新状态,进入下一轮或终止
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .llm import get_llm
from .memory import TrajectoryMemory
from .pattern_gate import PatternEligibilityGate
from .retrieval import RetrievalStream
from .rule_stream import RuleStream
from .specialists.adversarial_prober import AdversarialProber
from .specialists.graph_miner import GraphMiner
from .specialists.rule_composer import RuleComposer, Rule
from .specialists.shadow_evaluator import ShadowEvaluator
from .state import (
    Action, Outcome, State, Trajectory, TrajectoryStep, ACTION_TEMPLATES,
)

DATA_DIR = Path(__file__).parent.parent / "data"

SYSTEM_PROMPT = """You are an anti-fraud investigation orchestrator.

You investigate suspicious alerts by dispatching specialized tools (specialists),
one action per round. Separate case adjudication from rule production:
  1. Investigate the current case and gather evidence.
  2. If pattern_assessment.eligible is false, terminate/escalate the case WITHOUT
     generating a reusable rule.
  3. Only if pattern_assessment.eligible is true, generate a candidate rule,
     shadow-replay it, and adversarially probe it before termination.

# Hard constraints (Rule Stream — will reject actions that violate these)
- Graph queries: hop <= 2 (deeper queries exceed 100ms P99 latency)
- Rules must combine at least one STRUCTURE signal (shared_device/ip/contact)
  AND one ATTRIBUTE signal (new_account/night_apply/etc)
- Rules must have coverage_min >= 3
- Do NOT use forbidden data sources (contacts without consent, raw call records)

# Guards that only apply at `terminate` action (NOT at other actions)
- If label_maturity < 0.5 and you're about to confirm fraud with confidence > 0.8,
  either downgrade confidence to 0.6-0.7 and add "30-day recheck required" to
  recommendations, OR use escalate_to_human.
- If retrieval_confidence < 0.55 AND you're terminating with fraud_confirmed,
  use escalate_to_human instead. NOTE: at round 1-2, retrieval_confidence is
  naturally low because the suspect_set is small — this is EXPECTED, do NOT
  escalate prematurely. Only apply this guard when about to terminate.

# Preferences (learned from expert trajectories — simulated DPO alignment)
Priority order: LOW-FALSE-POSITIVE > EXPLAINABILITY > HIGH-RECALL > SPEED
- Prefer precise multi-condition rules over broad single-condition rules
- Prefer known-safe patterns (retrieved from memory) over novel guesses
- Only escalate when truly stuck (repeated rule violations, no matching precedent
  after 4+ rounds); do NOT escalate at round 1 just because retrieval is low.

# Available actions (choose ONE per round)
{action_templates}

# Output format
Return ONLY a JSON object:
{{"action_type": "...", "params": {{...}}, "rationale": "..."}}
"""


@dataclass
class OrchestratorConfig:
    """
    Orchestrator 配置。可以直接指定 use_* 三个开关,
    或用 mode 一键设置(mode 优先级更高)。

    mode 语义:
      - "baseline":   无 retrieval few-shot,无 alignment 偏好提示,只保留硬规则
      - "few_shot":   有 retrieval few-shot,无 alignment 偏好提示,硬规则保留
      - "dpo":        无 retrieval few-shot,无 alignment 偏好提示(偏好在权重里),硬规则保留
      - "dpo_retrieval": DPO 权重 + top-3 完整轨迹 retrieval + 硬规则
      - "full":       三流全开(retrieval + alignment + rules)
      - None(默认): 使用 use_* 三个字段的值
    """
    max_rounds: int = 8
    max_rule_retries: int = 2
    mode: str | None = None
    use_retrieval: bool = True
    use_full_trajectory_retrieval: bool = False
    use_alignment: bool = True
    use_rules: bool = True
    log_verbose: bool = True

    def __post_init__(self):
        if self.mode is None:
            return
        m = self.mode.lower()
        if m == "baseline":
            self.use_retrieval = False
            self.use_alignment = False
            self.use_rules = True
        elif m == "few_shot":
            self.use_retrieval = True
            self.use_alignment = False
            self.use_rules = True
        elif m == "dpo":
            # DPO 版本:偏好已经训进权重,prompt 里就不再叠加软偏好和 few-shot
            self.use_retrieval = False
            self.use_alignment = False
            self.use_rules = True
        elif m == "dpo_retrieval":
            # 论文 Full ACRM: DPO 偏好已在权重中；推理时仍提供 top-3
            # 完整历史轨迹，但不再重复注入软偏好提示。
            self.use_retrieval = True
            self.use_full_trajectory_retrieval = True
            self.use_alignment = False
            self.use_rules = True
        elif m == "full":
            self.use_retrieval = True
            self.use_alignment = True
            self.use_rules = True
        else:
            raise ValueError(f"Unknown mode: {self.mode}. "
                              "Use baseline / few_shot / dpo / dpo_retrieval / full or None.")


class Orchestrator:
    def __init__(self,
                 config: OrchestratorConfig | None = None,
                 memory: TrajectoryMemory | None = None):
        self.config = config or OrchestratorConfig()
        self.llm = get_llm()
        self.rule_stream = RuleStream()
        self.memory = memory or TrajectoryMemory()
        self.retrieval = RetrievalStream(self.memory)
        self.pattern_gate = PatternEligibilityGate()
        self.graph_miner = GraphMiner()
        self.rule_composer = RuleComposer()
        self.shadow = ShadowEvaluator()
        self.adversarial = AdversarialProber()
        self.df = pd.read_parquet(DATA_DIR / "graph_data.parquet")
        self._log_lines = []

    # ===== 主循环 =====

    def investigate(self, alert: dict) -> Trajectory:
        """一次告警的完整调查过程。"""
        start = time.time()
        traj = Trajectory(
            alert_id=alert["alert_id"],
            trigger_reason=alert["trigger_reason"],
        )
        # 初始状态
        state = State(
            alert_id=alert["alert_id"],
            round_num=0,
            suspect_set=[alert["seed_user"]],
        )
        # 首轮先跑一次 GraphMiner,给 LLM 一个初始诊断
        state = self._update_diagnostic(state)
        # 把 alert 的 trigger_reason 也拼进 diagnostic,方便 retrieval 匹配
        state.diagnostic_report = (
            f"Alert trigger: {alert['trigger_reason']}\n" + state.diagnostic_report
        )

        # 存最近一次的规则(供 __LATEST__ 引用)
        latest_rule: Rule | None = None
        shadow_report_last: dict | None = None

        for round_i in range(1, self.config.max_rounds + 1):
            state.round_num = round_i

            # 1. Retrieval
            retrieved = []
            state.retrieval_confidence = 1.0
            if self.config.use_retrieval:
                fingerprint = self._current_fingerprint(state)
                retrieved = self.retrieval.search(state, fingerprint, top_k=3)
                state.retrieval_confidence = self.retrieval.confidence(retrieved)

            # 个案调查与规则生产的确定性分流结果显式进入 State。
            state.pattern_assessment = self.pattern_gate.assess(state, traj).to_dict()

            # 2 + 3 + 4. Generate + Validate
            action = self._propose_and_validate(state, retrieved, traj)
            if action is None:
                self._log(f"[Round {round_i}] No valid action after retries — HANDOVER")
                traj.verdict = "escalate"
                break

            # 5. 执行
            outcome = self._execute(action, state, latest_rule, shadow_report_last)

            # 特化的产物记录
            if action.action_type == "generate_rule":
                latest_rule = outcome.metrics.get("_rule_obj")
            if action.action_type == "shadow_replay":
                shadow_report_last = outcome.metrics

            # 6. 记录
            traj.steps.append(TrajectoryStep(state=self._snapshot(state),
                                              action=action,
                                              outcome=outcome))
            state.action_history_summary.append(
                f"{action.short()} -> success={outcome.success}, note={outcome.note}"
            )

            # 7. 终止判定
            if action.action_type == "terminate":
                traj.verdict = self._normalize_verdict(
                    action.params.get("verdict", "unknown")
                )
                traj.final_confidence = float(action.params.get("confidence", 0.0))
                break
            if action.action_type == "escalate_to_human":
                traj.verdict = "escalate"
                break

            # 更新 state(某些动作会改变可疑集合或诊断)
            state = self._update_state_from_outcome(state, action, outcome)

        else:
            self._log(f"[Round {self.config.max_rounds}] max rounds reached — HANDOVER")
            traj.verdict = traj.verdict or "escalate"

        traj.total_seconds = time.time() - start
        traj.label = self._auto_label(traj, alert)
        self.memory.save(traj)
        return traj

    # ===== 内部工具 =====

    def _propose_and_validate(self, state: State, retrieved: list, traj: Trajectory) -> Action | None:
        """Generate-then-Validate 循环:LLM 生成 → Rule Stream 校验 → 违规重生成。"""
        error_feedback = None
        for attempt in range(self.config.max_rule_retries + 1):
            prompt = self._build_prompt(state, retrieved, error_feedback)
            raw = self.llm.chat([
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ])
            try:
                parsed = json.loads(raw)
                action = self._materialize_action(parsed, state, traj)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                error_feedback = f"Parse error: {e}. Return valid JSON with action_type/params."
                self._log(f"[Round {state.round_num}] LLM parse error: {e}")
                continue

            if not self.config.use_rules:
                self._log(f"[Round {state.round_num}] Rules DISABLED — accepting {action.short()}")
                return action

            violation = self.rule_stream.validate(action, state)
            if violation is None:
                self._log(f"[Round {state.round_num}] ✓ Proposed & validated: {action.short()}")
                return action
            self._log(f"[Round {state.round_num}] ✗ Rejected by {violation.rule_name}: {violation.message}")
            error_feedback = f"[{violation.rule_name}] {violation.message}"
        return None

    def _system_prompt(self) -> str:
        templates = "\n".join(
            f"- {name}: {info['description']} (params: {info['params']})"
            for name, info in ACTION_TEMPLATES.items()
        )
        prompt = SYSTEM_PROMPT.format(action_templates=templates)
        if not self.config.use_alignment:
            # 去掉 Preferences 段(消融用):
            # 保留 [头部...Guards 段] + [Available actions 段] + [Output format 段]
            before = prompt.split("# Preferences")[0].rstrip()
            after_pref = prompt.split("# Available actions", 1)
            if len(after_pref) == 2:
                prompt = before + "\n\n# Available actions" + after_pref[1]
        return prompt

    def _build_prompt(self, state: State, retrieved: list, error_feedback: str | None) -> str:
        parts = ["# Current investigation state\n" + json.dumps(state.to_prompt_dict(), indent=2)]
        if self.config.use_retrieval and retrieved:
            few_shot = []
            for r in retrieved:
                traj = r["trajectory"]
                sim = r["similarity"]
                if self.config.use_full_trajectory_retrieval:
                    few_shot.append(self._format_full_retrieved_trajectory(traj, sim))
                else:
                    few_shot.append(f"[Similarity {sim:.2f}] {traj.get('trigger_reason','')} "
                                     f"→ verdict={traj.get('verdict','?')}, rounds={traj.get('rounds','?')}, "
                                     f"actions=[{', '.join(s['action']['type'] for s in traj.get('steps', [])[:5])}]")
            parts.append("# Retrieved similar past trajectories\n" + "\n".join(few_shot))
        if error_feedback:
            parts.append(f"# ⚠ Previous attempt was rejected\n{error_feedback}\nRevise and retry.")
        parts.append("Return next action as JSON.")
        return "\n\n".join(parts)

    @staticmethod
    def _format_full_retrieved_trajectory(traj: dict, similarity: float) -> str:
        """按 DPO 训练表示序列化检索轨迹，供论文式 inference few-shot 使用。"""
        compact = lambda value: json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        lines = [
            f"[RETRIEVED TRAJECTORY | SIMILARITY={similarity:.2f}]",
            f"[DRIFT_TRIGGER] {traj.get('trigger_reason', '')}",
        ]
        for round_i, step in enumerate(traj.get("steps", []), 1):
            action = step.get("action", {})
            lines.extend([
                f"[ROUND {round_i}]",
                f"<STATE> {compact(step.get('state', {}))}",
                f"<ACTION> {compact({'action_type': action.get('type'), 'params': action.get('params', {}), 'rationale': action.get('rationale', '')})}",
                f"<OUTCOME> {compact(step.get('outcome', {}))}",
            ])
        lines.append(f"[RESULT] {compact({'verdict': traj.get('verdict', ''), 'confidence': traj.get('final_confidence', 0.0), 'rounds': len(traj.get('steps', []))})}")
        return "\n".join(lines)

    def _materialize_action(self, parsed: dict, state: State, traj: Trajectory) -> Action:
        params = dict(parsed.get("params", {}))
        # 替换特殊占位
        if params.get("seeds") == "__FROM_STATE__":
            params["seeds"] = state.suspect_set
        if params.get("rule_id") == "__LATEST__":
            latest = self._find_latest_rule_id(traj)
            if latest:
                params["rule_id"] = latest
        return Action(
            action_type=parsed["action_type"],
            params=params,
            rationale=parsed.get("rationale", ""),
        )

    def _find_latest_rule_id(self, traj: Trajectory) -> str | None:
        for step in reversed(traj.steps):
            if step.action.action_type == "generate_rule":
                return step.outcome.metrics.get("rule_id")
        return None

    def _execute(self, action: Action, state: State,
                 latest_rule: Rule | None, shadow_report_last: dict | None) -> Outcome:
        t = action.action_type
        try:
            if t == "expand_neighbors":
                seeds = action.params.get("seeds", state.suspect_set)
                hop = int(action.params.get("hop", 1))
                edge = action.params.get("edge_type")
                new_users = self.graph_miner.expand_neighbors(seeds, hop=hop, edge_type=edge)
                added = [u for u in new_users if u not in state.suspect_set]
                return Outcome(success=True,
                               metrics={"added": len(added), "total_suspects": len(new_users)},
                               note=f"expanded {hop}-hop via {edge}",
                               new_suspects=new_users)
            if t == "find_community":
                comms = self.graph_miner.find_community(state.suspect_set,
                                                        min_size=int(action.params.get("min_size", 3)))
                return Outcome(success=True,
                               metrics={"communities": len(comms),
                                        "largest_size": len(comms[0]) if comms else 0},
                               note=f"found {len(comms)} communities")
            if t == "check_shared_entity":
                etype = action.params.get("entity_type", "device_id")
                stats = self.graph_miner.shared_entity_stats(state.suspect_set)
                return Outcome(success=True,
                               metrics={"shared_entities_of_type": len(stats.get(etype, []))},
                               note=f"shared {etype} entries")
            if t == "check_temporal_burst":
                ts_map = self.df.set_index("user_id")["timestamp"].to_dict()
                ts_sub = {u: ts_map[u] for u in state.suspect_set if u in ts_map}
                burst = self.graph_miner.temporal_burst(state.suspect_set, ts_sub,
                                                        window_hours=int(action.params.get("window_hours", 4)))
                return Outcome(success=True, metrics=burst, note="temporal burst check")
            if t == "compute_risk_score":
                m = self.graph_miner.compute_metrics(state.suspect_set, self.df)
                # 综合分:多个属性维度加权
                risk = (m.get("new_account_ratio", 0) * 0.4 +
                        m.get("night_apply_ratio", 0) * 0.2 +
                        m.get("paste_used_ratio", 0) * 0.2 +
                        (1 - min(m.get("avg_input_speed_ms", 3000) / 3000, 1)) * 0.2)
                return Outcome(success=True,
                               metrics={"risk_score": round(risk, 3), **m},
                               note="composite risk score")
            if t == "generate_rule":
                diag = self._current_diagnostic(state)
                rule = self.rule_composer.compose_from_diagnostic(diag, state.suspect_set, self.df)
                return Outcome(success=True,
                               metrics={"rule_id": rule.rule_id,
                                        "pattern": rule.pattern,
                                        "coverage_est": rule.coverage_est,
                                        "fp_rate_est": rule.fp_rate_est,
                                        "_rule_obj": rule},
                               note=f"generated {rule.rule_id}")
            if t == "shadow_replay":
                if latest_rule is None:
                    return Outcome(success=False, note="no rule to replay",
                                   metrics={"error": "no_rule"})
                days = int(action.params.get("replay_days", 7))
                rep = self.shadow.replay(latest_rule, days=days)
                return Outcome(success=True, metrics=rep, note=f"replay on {days} days")
            if t == "adversarial_probe":
                if latest_rule is None:
                    return Outcome(success=False, note="no rule to probe",
                                   metrics={"error": "no_rule"})
                probe = self.adversarial.probe(latest_rule)
                return Outcome(success=True,
                               metrics={"verdict": probe["verdict"],
                                        "bypass_count": probe["bypass_count"]},
                               note="; ".join(f"{f['strategy']}:{'✗' if f['can_bypass'] else '✓'}"
                                              for f in probe["bypass_findings"]))
            if t == "escalate_to_human":
                return Outcome(success=True, metrics={"reason": action.params.get("reason", "")},
                               note="handover")
            if t == "terminate":
                return Outcome(success=True,
                               metrics={"verdict": action.params.get("verdict"),
                                        "confidence": action.params.get("confidence")},
                               note="terminate")
        except Exception as e:
            return Outcome(success=False, note=f"exec error: {e}", metrics={"error": str(e)})
        return Outcome(success=False, note=f"unknown action {t}", metrics={})

    def _update_state_from_outcome(self, state: State, action: Action, outcome: Outcome) -> State:
        if action.action_type == "expand_neighbors" and outcome.new_suspects:
            state.suspect_set = list(set(state.suspect_set) | set(outcome.new_suspects))
            state = self._update_diagnostic(state)
        return state

    def _update_diagnostic(self, state: State) -> State:
        diag = self.graph_miner.analyze(state.suspect_set, self.df)
        state.diagnostic_report = diag["report"]
        state.key_metrics = diag["metrics"]
        state.label_maturity = diag["metrics"].get("avg_label_maturity", 0.5)
        state.graph_fingerprint = diag["fingerprint"]
        return state

    def _current_diagnostic(self, state: State) -> dict:
        return self.graph_miner.analyze(state.suspect_set, self.df)

    def _current_fingerprint(self, state: State) -> dict:
        return self.graph_miner.analyze(state.suspect_set, self.df)["fingerprint"]

    def _snapshot(self, state: State) -> State:
        # 浅拷贝(不动可变字段)
        return State(
            alert_id=state.alert_id,
            round_num=state.round_num,
            diagnostic_report=state.diagnostic_report,
            suspect_set=list(state.suspect_set),
            key_metrics=dict(state.key_metrics),
            label_maturity=state.label_maturity,
            action_history_summary=list(state.action_history_summary),
            retrieval_confidence=state.retrieval_confidence,
            graph_fingerprint=dict(state.graph_fingerprint),
            pattern_assessment=dict(state.pattern_assessment),
        )

    @staticmethod
    def _normalize_verdict(verdict: str) -> str:
        aliases = {
            "escalate_to_human": "escalate",
            "human_review": "escalate",
            "manual_review": "escalate",
            "legitimate": "not_fraud",
            "fraudulent": "fraud_confirmed",
        }
        return aliases.get(str(verdict).strip().lower(), str(verdict).strip().lower())

    def _auto_label(self, traj: Trajectory, alert: dict) -> str:
        """
        依据真实标签评估:调查判定是否正确。
        用于事后打 accepted/rejected 供 DPO 训练。
        """
        # 评测集可按金标严格判定；线上新轨迹必须先进入人工审核队列，
        # 不能因为模型“高置信”就自动污染检索记忆或 DPO 数据。
        expected = alert.get("expected_verdict")
        if expected:
            return "accepted" if traj.verdict == self._normalize_verdict(expected) else "rejected"
        return "pending_review"

    def _log(self, s: str):
        if self.config.log_verbose:
            print(s)
        self._log_lines.append(s)
