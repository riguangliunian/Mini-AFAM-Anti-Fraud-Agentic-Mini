# DPO 训练指南 — 服务器操作步骤

一份从 Mac 本地把数据 + 代码上传到服务器,训练 Qwen3-4B DPO,再拉回本地评测的完整流程。

## 一、要传的文件

从本地 `/Users/didi/mini_afam/` 复制这几个到服务器:

```bash
# 关键文件
logs/dpo_train.jsonl           # 116 条偏好对
experiments/train_dpo.py       # DPO 训练脚本

# 建议一起传(方便服务器上跑评测)
src/                           # 整个 src 目录
data/eval_alerts.json          # 评测集
experiments/compare_modes.py   # 评测脚本
experiments/evaluate.py
```

传法:

```bash
# 从本机执行
rsync -av \
    /Users/didi/mini_afam/logs/dpo_train.jsonl \
    /Users/didi/mini_afam/experiments/ \
    /Users/didi/mini_afam/src/ \
    /Users/didi/mini_afam/data/eval_alerts.json \
    user@your-server:~/mini_afam_dpo/
```

或者 `tar czf` 后 `scp` 传。

## 二、服务器环境准备

```bash
cd ~/mini_afam_dpo

# 建议用 conda / venv 隔离环境
python -m venv venv && source venv/bin/activate

pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers>=4.45 trl>=0.11 peft>=0.13 accelerate datasets bitsandbytes

# 如果要用 wandb 监控训练
pip install wandb
wandb login
```

## 三、下载 base 模型

```bash
# 方式一:HuggingFace CLI
pip install huggingface-hub
huggingface-cli download Qwen/Qwen3-4B-Instruct-2507 --local-dir ./base_model

# 方式二:直接让 trainer 自动下载(需要能连 HuggingFace 或 mirror)
export HF_ENDPOINT=https://hf-mirror.com  # 国内镜像,可选
```

## 四、开始训练

### 单卡(≥24GB,推荐 4090/A10/L40)

```bash
python experiments/train_dpo.py \
    --model_name Qwen/Qwen3-4B-Instruct-2507 \
    --data_path logs/dpo_train.jsonl \
    --output_dir ./qwen3-4b-dpo \
    --num_epochs 3 \
    --batch_size 2 \
    --grad_accum 4 \
    --lr 5e-6 \
    --beta 0.1
```

**预期训练时间**:
- 116 pairs × 3 epochs = 348 steps
- 单卡 4090: 30-60 分钟
- 单卡 A100: 20-40 分钟

### QLoRA(16GB 显存也能跑,如 3060/A4000)

```bash
python experiments/train_dpo.py \
    --model_name Qwen/Qwen3-4B-Instruct-2507 \
    --data_path logs/dpo_train.jsonl \
    --output_dir ./qwen3-4b-dpo \
    --use_qlora \
    --batch_size 1 \
    --grad_accum 8
```

**预期训练时间**:比全精度慢 15-20%,约 45-90 分钟。

## 五、训完后合并 LoRA(方便部署)

```bash
python -c "
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

base = AutoModelForCausalLM.from_pretrained(
    'Qwen/Qwen3-4B-Instruct-2507',
    torch_dtype=torch.bfloat16
)
merged = PeftModel.from_pretrained(base, './qwen3-4b-dpo').merge_and_unload()
merged.save_pretrained('./qwen3-4b-dpo-merged')
tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-4B-Instruct-2507')
tok.save_pretrained('./qwen3-4b-dpo-merged')
"
```

## 六、部署 DPO 后的模型

### 方式 A:vLLM(推荐,速度快)

```bash
pip install vllm

vllm serve ./qwen3-4b-dpo-merged \
    --host 0.0.0.0 --port 8000 \
    --served-model-name qwen3-4b-dpo
```

从本地跑评测:
```bash
export OPENAI_BASE_URL=http://your-server:8000/v1
export LLM_MODEL=qwen3-4b-dpo
python -m experiments.compare_modes --modes dpo
```

### 方式 B:转成 GGUF 给 Ollama

```bash
# 需要 clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
python convert_hf_to_gguf.py ../qwen3-4b-dpo-merged \
    --outfile qwen3-4b-dpo.gguf \
    --outtype q4_k_m

# 传回本地
scp your-server:~/llama.cpp/qwen3-4b-dpo.gguf ~/mini_afam/

# 本地导入 Ollama
cat > Modelfile <<EOF
FROM ./qwen3-4b-dpo.gguf
TEMPLATE "..."  # 从 Qwen3 官方 chat template 复制
EOF
ollama create qwen3-4b-dpo -f Modelfile
```

## 七、完整评测(DPO vs baseline vs few-shot)

```bash
# 本地
cd /Users/didi/mini_afam
export OPENAI_BASE_URL=http://your-server:8000/v1  # 或本地 Ollama
export LLM_MODEL=qwen3-4b-dpo

# 一次跑 3 组 mode
python -m experiments.compare_modes --modes baseline few_shot dpo

# 结果在 logs/compare_qwen3-4b-dpo_summary.md
```

## 八、预期指标改进

参考 baseline vs few_shot 的对比结果:

| Mode | Strict | Lenient | 说明 |
|---|---|---|---|
| baseline | 41.2% | 41.2% | 无偏好,过度自信 |
| few_shot | 47.1% | 91.2% | 检索历史成功轨迹 |
| **dpo** | **预期 55-70%** | **预期 90-98%** | 偏好训进权重 |

DPO 应该在:
- **B 类**(subtle immature):不再自创 `fraud_probable`,一致使用 `escalate` 或降置信度 `fraud_confirmed`
- **E 类**(novel pattern):不再自创 `fraud_pending` / `fraud_likelihood_high`,一致使用 `escalate`
- **规则质量**:保持 75%+ recall / 99% precision(不应下降)

如果 DPO 效果不如预期,常见原因:
1. **数据量太少**(116 条) → 扩到 300-500 条会稳定得多
2. **β 太高**(默认 0.1)→ 降到 0.05,让模型更愿偏离 base
3. **训练 epoch 不足** → 试 5 epochs
4. **learning rate 太小** → 试 1e-5

## 九、故障排查

**OOM(显存不够)**:
- 用 `--use_qlora`
- 减 `--batch_size 1 --grad_accum 8`
- 缩 `--max_length 1024`

**训练 loss 不降**:
- 检查数据格式:`head -1 logs/dpo_train.jsonl | python -m json.tool`
- 每条应有 `prompt / chosen / rejected` 三字段
- Chosen 和 rejected 应该有明显差异

**训完效果和 baseline 一样**:
- 大概率 LoRA 没生效 → 检查 `trainer.model.print_trainable_parameters()` 的输出
- 或者 β 太高,模型不敢偏离 base → 降到 0.05
