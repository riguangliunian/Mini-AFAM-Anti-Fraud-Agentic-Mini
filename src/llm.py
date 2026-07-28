"""
LLM 适配层。支持四种后端:
- Ollama 本地(默认识别 localhost:11434,例如 qwen3:4b)
- OpenAI 兼容 API(通过 OPENAI_API_KEY 环境变量)
- Transformers 本地模型(通过 LOCAL_MODEL_PATH 环境变量)
- Mock 模式(无 API,启发式规则驱动)

设计原则:
- Orchestrator 只依赖 chat(messages) 接口
- 环境变量 LLM_MODEL 选后端 + 模型名
- 环境变量 OPENAI_BASE_URL 覆盖 endpoint(Ollama 会自动检测)
"""

import json
import os
import re
from typing import Any


# --------------------------------------------------------------------------------------
# Mock LLM(不变,启发式驱动,用于快速冒烟测试)
# --------------------------------------------------------------------------------------

class MockLLM:
    """无 API 的启发式后端。"""

    def chat(self, messages: list[dict[str, str]]) -> str:
        user_msg = messages[-1]["content"]
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
        pattern_eligible = bool(state.get("pattern_assessment", {}).get("eligible", False))

        error_feedback = ""
        m_err = re.search(r"Previous attempt was rejected\n(.+?)(?:\nRevise|$)",
                          user_msg, re.DOTALL)
        if m_err:
            error_feedback = m_err.group(1)

        if "NOVEL_PATTERN_GUARD" in error_feedback or "LABEL_MATURITY_GUARD" in error_feedback:
            return json.dumps({
                "action_type": "escalate_to_human",
                "params": {"reason": f"Rule Stream guard triggered: {error_feedback[:120]}"},
                "rationale": "Complying with Rule Stream — switching to escalate.",
            })
        if "PATTERN_NOT_REUSABLE" in error_feedback:
            return json.dumps({
                "action_type": "escalate_to_human",
                "params": {"reason": "Case evidence is insufficient for reusable rule production."},
                "rationale": "Keep this as a case decision and request review instead of overfitting a rule.",
            })
        if ("STRUCTURE_ONLY_RULE" in error_feedback
                or "INCOMPLETE_RULE_EVIDENCE" in error_feedback
                or "COVERAGE_TOO_LOW" in error_feedback):
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
        if (pattern_eligible and "generate_rule" not in past_actions_str
                and "communities" in diag.lower()):
            return json.dumps({
                "action_type": "generate_rule",
                "params": {"pattern": "auto", "coverage_min": 3, "confidence_threshold": 0.7},
                "rationale": "Diagnostic shows communities; propose combined rule.",
            })
        if "generate_rule" in past_actions_str and "shadow_replay" not in past_actions_str:
            return json.dumps({
                "action_type": "shadow_replay",
                "params": {"rule_id": "__LATEST__", "replay_days": 7},
                "rationale": "Validate rule performance on 7-day replay.",
            })
        if "shadow_replay" in past_actions_str and "adversarial_probe" not in past_actions_str:
            return json.dumps({
                "action_type": "adversarial_probe",
                "params": {"rule_id": "__LATEST__", "bypass_strategies": "all"},
                "rationale": "Red-team the rule before terminate.",
            })
        if conf < 0.6 and len(past_actions_list) < 3:
            return json.dumps({
                "action_type": "escalate_to_human",
                "params": {"reason": f"Low retrieval confidence ({conf:.2f}) at early round; novel pattern."},
                "rationale": "Retrieval below 0.6 threshold at early round — handover.",
            })
        verdict = "fraud_confirmed" if "gang" in diag.lower() or "burst" in diag.lower() else "not_fraud"
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


# --------------------------------------------------------------------------------------
# OpenAI-compatible backend(支持 OpenAI API / compatible proxy / Ollama 本地)
# --------------------------------------------------------------------------------------

class OpenAILLM:
    """
    OpenAI 兼容后端,可对接:
    - OpenAI 官方 (OPENAI_API_KEY)
    - OpenAI-compatible proxy (OPENAI_BASE_URL 指定)
    - Ollama 本地 (OPENAI_BASE_URL=http://localhost:11434/v1)

    自动识别 Ollama endpoint 并做兼容处理(JSON mode 支持稍弱,用 prompt 引导)。
    """

    def __init__(self, model: str | None = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("pip install openai first, or set LLM_MODEL=mock")

        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("OPENAI_BASE_URL")
        # Ollama 检测
        self.is_ollama = bool(base_url and ("11434" in base_url or "ollama" in base_url.lower()))

        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        # Ollama 不需要真 key,但 openai 客户端要求非空
        if self.is_ollama and not os.environ.get("OPENAI_API_KEY"):
            kwargs["api_key"] = "ollama-local"
        kwargs["timeout"] = float(os.environ.get("OPENAI_TIMEOUT", "60"))
        self.client = OpenAI(**kwargs)

    def chat(self, messages: list[dict[str, str]]) -> str:
        # 可通过 LLM_TEMPERATURE 环境变量覆盖(供多样性采样用)
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        create_kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        # Ollama 目前 JSON mode 支持不完整,不强制;OpenAI-compatible endpoint 强制 JSON
        if not self.is_ollama:
            create_kwargs["response_format"] = {"type": "json_object"}

        # Qwen3 thinking 模式对我们的确定性动作生成有害,关闭
        if "qwen3" in self.model.lower():
            create_kwargs["extra_body"] = {"enable_thinking": False}

        resp = self.client.chat.completions.create(**create_kwargs)
        content = resp.choices[0].message.content
        # Ollama 有时会在 JSON 前后带 ```json``` fence,清理
        return _strip_code_fence(content)


# --------------------------------------------------------------------------------------
# Transformers 本地后端(服务器直接加载 HuggingFace/合并后的 LoRA 模型)
# --------------------------------------------------------------------------------------

class LocalTransformersLLM:
    """在当前进程中直接加载本地 HuggingFace causal LM。"""

    def __init__(self, model_path: str):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                "Local Transformers backend requires: pip install torch transformers accelerate"
            ) from e

        self.torch = torch
        self.model_path = model_path
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True,
            # 某些 Qwen3 合并目录会把 extra_special_tokens 保存成 []，
            # 新版 Transformers 期望 dict；显式覆盖以兼容两种格式。
            extra_special_tokens={},
        )
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA is unavailable. Check with: python -c \"import torch; "
                "print(torch.version.cuda, torch.cuda.is_available())\""
            )

        dtype_name = os.environ.get("LOCAL_MODEL_DTYPE", "bfloat16").lower()
        dtype_map = {
            "bfloat16": torch.bfloat16,
            "bf16": torch.bfloat16,
            "float16": torch.float16,
            "fp16": torch.float16,
            "float32": torch.float32,
            "fp32": torch.float32,
        }
        if dtype_name not in dtype_map:
            raise ValueError(f"Unsupported LOCAL_MODEL_DTYPE={dtype_name}")

        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=dtype_map[dtype_name],
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        self.model.eval()

    def chat(self, messages: list[dict[str, str]]) -> str:
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        max_new_tokens = int(os.environ.get("LOCAL_MAX_NEW_TOKENS", "512"))

        template_kwargs = dict(
            tokenize=False,
            add_generation_prompt=True,
        )
        # Qwen3 chat template 支持该参数；普通模板会忽略/拒绝它，因此仅对 Qwen3 设置。
        model_name = str(self.model_path).lower()
        if "qwen3" in model_name:
            template_kwargs["enable_thinking"] = False
        try:
            prompt = self.tokenizer.apply_chat_template(messages, **template_kwargs)
        except TypeError:
            template_kwargs.pop("enable_thinking", None)
            prompt = self.tokenizer.apply_chat_template(messages, **template_kwargs)

        inputs = self.tokenizer(prompt, return_tensors="pt")
        input_device = next(self.model.parameters()).device
        inputs = {k: v.to(input_device) for k, v in inputs.items()}
        do_sample = temperature > 0
        generate_kwargs = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if do_sample:
            generate_kwargs["temperature"] = temperature

        with self.torch.inference_mode():
            output = self.model.generate(**generate_kwargs)
        generated = output[0, inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(generated, skip_special_tokens=True)
        return _strip_code_fence(text)


def _strip_code_fence(text: str) -> str:
    """去掉可能的 ```json ... ``` 包裹。"""
    if not text:
        return text
    text = text.strip()
    m = re.match(r"```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


# --------------------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------------------

def get_llm():
    """
    环境变量:
    - LLM_MODEL=mock                    → MockLLM
    - LLM_MODEL=local + LOCAL_MODEL_PATH=/path/to/model → Transformers 本地模型
    - LLM_MODEL=gpt-4o-mini(默认)      → OpenAILLM
    - LLM_MODEL=qwen3:4b + OPENAI_BASE_URL=http://localhost:11434/v1  → Ollama 本地
    - LLM_MODEL=qwen-plus + OPENAI_BASE_URL=https://your-compatible-endpoint/v1 → OpenAI-compatible proxy
    """
    model = os.environ.get("LLM_MODEL", "mock")
    if model.lower() == "mock":
        return MockLLM()
    local_model_path = os.environ.get("LOCAL_MODEL_PATH")
    if model.lower() in {"local", "transformers"} or local_model_path:
        if not local_model_path:
            raise RuntimeError("Set LOCAL_MODEL_PATH to the merged model directory")
        return LocalTransformersLLM(local_model_path)
    return OpenAILLM(model=model)
