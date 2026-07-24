"""
DPO 训练脚本(在线上服务器跑)。

依赖(在服务器 pip 安装):
    pip install torch transformers trl peft accelerate datasets bitsandbytes

用法:
    # 单卡(24GB+ GPU,如 3090/4090/A10)
    python train_dpo.py \
        --model_name Qwen/Qwen3-4B-Instruct-2507 \
        --data_path logs/dpo_train.jsonl \
        --output_dir ./qwen3-4b-dpo \
        --num_epochs 3

    # QLoRA(GPU 显存不够时,4-bit 量化)
    python train_dpo.py \
        --model_name Qwen/Qwen3-4B-Instruct-2507 \
        --data_path logs/dpo_train.jsonl \
        --output_dir ./qwen3-4b-dpo \
        --use_qlora

    # 多卡(deepspeed / accelerate)
    accelerate launch train_dpo.py ...

训完后,导出为 Ollama 兼容 GGUF 或直接用 vLLM serve:
    vllm serve ./qwen3-4b-dpo --host 0.0.0.0 --port 8000

    # 或转 GGUF 给 Ollama(需要 llama.cpp 的 convert-hf-to-gguf.py)
    python convert-hf-to-gguf.py ./qwen3-4b-dpo --outfile qwen3-4b-dpo.gguf --outtype q4_k_m
"""

import argparse
import json
try:
    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer
except ImportError as e:
    print("Missing dependencies. Install with:")
    print("  pip install torch transformers trl peft accelerate datasets bitsandbytes")
    raise


def load_dpo_dataset(path: str) -> "Dataset":
    """把 dpo_train.jsonl 加载为 HF Dataset。TRL DPOTrainer 需要 prompt/chosen/rejected 三列。"""
    data = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            data.append({
                "prompt": obj["prompt"],
                "chosen": obj["chosen"],
                "rejected": obj["rejected"],
            })
    return Dataset.from_list(data)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model_name", default="Qwen/Qwen3-4B-Instruct-2507",
                    help="HuggingFace model ID or local path")
    p.add_argument("--data_path", default="logs/dpo_train.jsonl")
    p.add_argument("--eval_data_path", default=None,
                    help="held-out preference JSONL; enables epoch evaluation")
    p.add_argument("--output_dir", default="./qwen3-4b-dpo")
    p.add_argument("--num_epochs", type=int, default=3)
    p.add_argument("--batch_size", type=int, default=2,
                    help="per-device batch size (each preference pair counts as 1)")
    p.add_argument("--grad_accum", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-6)
    p.add_argument("--beta", type=float, default=0.1, help="DPO temperature (β)")
    p.add_argument("--max_length", type=int, default=8192,
                    help="paper Appendix E.5 uses 8192 for full trajectories")
    p.add_argument("--max_prompt_length", type=int, default=1024,
                    help="shared scenario/trigger prompt is short; reserve tokens for trajectories")
    p.add_argument("--lora_r", type=int, default=64)
    p.add_argument("--lora_alpha", type=int, default=128)
    p.add_argument("--target_modules", nargs="+",
                    default=["q_proj", "k_proj", "v_proj", "o_proj"],
                    help="paper Appendix E.5 adapts all attention Q/K/V/O layers")
    p.add_argument("--use_qlora", action="store_true",
                    help="4-bit quantize base model (for <24GB VRAM)")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    print(f"Loading data from {args.data_path}...")
    dataset = load_dpo_dataset(args.data_path)
    eval_dataset = load_dpo_dataset(args.eval_data_path) if args.eval_data_path else None
    print(f"  Total pairs: {len(dataset)}")
    print(f"  Sample keys: {list(dataset[0].keys())}\n")

    # ---- Tokenizer ----
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ---- Model(可选 QLoRA)----
    bnb_config = None
    if args.use_qlora:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    print(f"Loading model {args.model_name}...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=torch.bfloat16,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    if args.use_qlora:
        model = prepare_model_for_kbit_training(model)

    # ---- LoRA ----
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=args.target_modules,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ---- DPO Trainer ----
    dpo_config = DPOConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        beta=args.beta,
        max_length=args.max_length,
        max_prompt_length=args.max_prompt_length,
        logging_steps=5,
        save_strategy="epoch",
        eval_strategy="epoch" if eval_dataset is not None else "no",
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        save_total_limit=2,
        bf16=True,
        gradient_checkpointing=True,
        remove_unused_columns=False,
        report_to="none",  # 改成 "wandb" 上报 wandb
        seed=args.seed,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # LoRA + None → 自动用冻结的 base 作为 ref
        args=dpo_config,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    print("\n===== Start DPO training =====\n")
    trainer.train()

    # 保存 LoRA adapter
    print(f"\nSaving LoRA adapter to {args.output_dir}...")
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    # 如果要合并 LoRA 到 base 得到完整 checkpoint(方便部署):
    print("\nTo merge LoRA into base model for deployment, run:")
    print(f"  python -c \"from peft import PeftModel; from transformers import AutoModelForCausalLM;")
    print(f"    base = AutoModelForCausalLM.from_pretrained('{args.model_name}', torch_dtype='bfloat16');")
    print(f"    merged = PeftModel.from_pretrained(base, '{args.output_dir}').merge_and_unload();")
    print(f"    merged.save_pretrained('{args.output_dir}_merged')\"")


if __name__ == "__main__":
    main()
