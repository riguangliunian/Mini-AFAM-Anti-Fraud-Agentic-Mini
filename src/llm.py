"""
LLM 适配层。支持三种模式:
- OpenAI 兼容 API (默认,使用 OPENAI_API_KEY)
- Mock 模式(无 API,用规则驱动的启发式模拟)

设计原则:
- Orchestrator 只依赖 chat(messages) 接口
- 切换后端只需换 LLM 客户端
"""

import json
import os
import re
from typing import Any


class MockLLM:
    """
    无 API 的启发式后端。
    用于:CI 测试、离线开发、演示时"model=mock"对照组。

    策略:
    - 根据 diagnostic report 里的关键词决定下一步
    - 优先执行"扩展 → 分析 → 生成规则 → 影子测试 → 红队 → 终止"这个默认路径
    """

    def chat(self, messages: list[dict[str, str]]) -> str:
        user_msg = messages[-1]["content"]
        # 从 prompt 里解析当前状态(JSON 块位于 "# Current investigation state\n" 之后)
        state = {}
        m = re.search(r"# Current investigation state\n(\{.*?\n\})",
                      user_msg, re.DOTALL)
        if m:
            try:
                state = json.loads(m.group(1))
            except json.JSONDecodeError:
                state = {}
        past_actions_list = state.get("past_actions", [])
        past_actions_str = " | ".join(past_actions_list)
        diag = state.get("diagnostic_report", "")
        conf = float(state.get("retrieval_confidence", 1.0))
        maturity = float(state.get("label_maturity", 0.5))

        # 是否收到 Rule Stream 的错误反馈?若是则据错误信息调整
        error_feedback = ""
        m_err = re.search(r"Previous attempt was rejected\n(.+?)(?:\nRevise|$)",
                          user_msg, re.DOTALL)
        if m_err:
            error_feedback = m_err.group(1)

        # 响应特定护栏错误
        if "NOVEL_PATTERN_GUARD" in error_feedback or "LABEL_MATURITY_GUARD" in error_feedback:
            return json.dumps({
                "action_type": "escalate_to_human",
                "params": {"reason": f"Rule Stream guard triggered: {error_feedback[:120]}"},
                "rationale": "Complying with Rule Stream — switching to escalate.",
            })
        if "STRUCTURE_ONLY_RULE" in error_feedback or "COVERAGE_TOO_LOW" in error_feedback:
            return json.dumps({
                "action_type": "generate_rule",
                "params": {"pattern": "shared_device_id AND is_new_account AND night_apply",
                           "coverage_min": 5, "confidence_threshold": 0.75},
                "rationale": "Adding attribute signal / raising coverage per Rule Stream.",
            })
        if "MAX_HOP_EXCEEDED" in error_feedback:
            return json.dumps({
                "action_type": "expand_neighbors",
                "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": "device_id"},
                "rationale": "Reducing hop to 1 per Rule Stream constraint.",
            })

        # 决策树
        # 1. 首轮 -> 图扩展(边类型按 alert trigger 选)
        if "expand_neighbors" not in past_actions_str:
            if "contact" in diag.lower():
                edge_type = "contact"
            elif "ip shared" in diag.lower():
                edge_type = "ip"
            else:
                edge_type = "device_id"
            return json.dumps({
                "action_type": "expand_neighbors",
                "params": {"seeds": "__FROM_STATE__", "hop": 1, "edge_type": edge_type},
                "rationale": f"First round: 1-hop {edge_type} expansion.",
            })
        # 2. 已经扩展但还没生成规则,且有诊断报告 -> 生成规则
        if "generate_rule" not in past_actions_str and "communities" in diag.lower():
            return json.dumps({
                "action_type": "generate_rule",
                "params": {"pattern": "auto", "coverage_min": 3, "confidence_threshold": 0.7},
                "rationale": "Diagnostic shows communities; propose combined rule.",
            })
        # 3. 已生成规则 -> shadow replay
        if "generate_rule" in past_actions_str and "shadow_replay" not in past_actions_str:
            return json.dumps({
                "action_type": "shadow_replay",
                "params": {"rule_id": "__LATEST__", "replay_days": 7},
                "rationale": "Validate rule performance on 7-day replay.",
            })
        # 4. shadow OK -> 红队
        if "shadow_replay" in past_actions_str and "adversarial_probe" not in past_actions_str:
            return json.dumps({
                "action_type": "adversarial_probe",
                "params": {"rule_id": "__LATEST__", "bypass_strategies": "all"},
                "rationale": "Red-team the rule before terminate.",
            })
        # 5. 只有早期(信息不足时)才因为低置信度 escalate;
        #    完成了完整调查链的话,依然走 terminate。
        if conf < 0.6 and len(past_actions_list) < 3:
            return json.dumps({
                "action_type": "escalate_to_human",
                "params": {"reason": f"Low retrieval confidence ({conf:.2f}) at early round; novel pattern."},
                "rationale": "Retrieval below 0.6 threshold at early round — handover.",
            })
        # 6. 默认 terminate
        verdict = "fraud_confirmed" if "gang" in diag.lower() or "burst" in diag.lower() else "not_fraud"
        # 标签不成熟时降级
        if maturity < 0.5 and verdict == "fraud_confirmed":
            confidence = 0.6
            recs = ["30-day recheck required due to immature labels"]
        else:
            confidence = 0.85 if verdict == "fraud_confirmed" else 0.7
            recs = ["deploy rule with 5% ramp"] if verdict == "fraud_confirmed" else ["release from watchlist"]

        return json.dumps({
            "action_type": "terminate",
            "params": {"verdict": verdict, "confidence": confidence, "recommendations": recs},
            "rationale": "All investigation steps complete; issue verdict.",
        })


class OpenAILLM:
    """OpenAI 兼容后端(可对接任何 OpenAI-format API)。"""

    def __init__(self, model: str | None = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("pip install openai first, or set LLM_MODEL=mock")
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("OPENAI_BASE_URL")
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

    def chat(self, messages: list[dict[str, str]]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content


def get_llm():
    """按环境变量选后端。"""
    model = os.environ.get("LLM_MODEL", "mock").lower()
    if model == "mock":
        return MockLLM()
    return OpenAILLM(model=model)
