"""Generate the Kaggle training notebook with benchmark evaluation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "ARIS_N-ATLaS_Kaggle.ipynb"
NB.parent.mkdir(parents=True, exist_ok=True)

cells = []
def md(s): cells.append({"cell_type":"markdown","metadata":{},"source":s.splitlines(True)})
def code(s): cells.append({"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":s.splitlines(True)})

md("""# ARIS powered by N-ATLaS
## Kaggle QLoRA fine-tuning + 500-case benchmark evaluation

### Before running
1. Upload to a Kaggle Dataset:
   - `data/processed/aris_natlas_train_v1.jsonl` (or `aris_expanded_training_v1.jsonl`)
   - `data/processed/aris_natlas_validation_v1.jsonl`
   - `data/processed/aris_benchmark_500_v1.jsonl`
2. Enable a GPU accelerator.
3. Add a Kaggle secret `HF_TOKEN` with your Hugging Face token.
4. Confirm your HF account has access to `NCAIR1/N-ATLaS`.
""")

md("## Cell 1 — Install pinned dependencies")
code("""%pip install -q transformers==4.48.3 datasets==3.2.0 peft==0.14.0 accelerate==1.2.1 bitsandbytes==0.45.0
""")

md("## Cell 2 — Authenticate and locate datasets")
code("""import os, json, glob, hashlib, torch
from pathlib import Path
from huggingface_hub import login
from kaggle_secrets import UserSecretsClient

assert torch.cuda.is_available(), "Enable a Kaggle GPU accelerator."
print("GPU:", torch.cuda.get_device_name(0))

try:
    hf_token = UserSecretsClient().get_secret("HF_TOKEN")
except Exception as e:
    raise RuntimeError("Add a Kaggle secret named HF_TOKEN.") from e
login(token=hf_token, add_to_git_credential=False)

def locate(name):
    matches = glob.glob("/kaggle/input/**/" + name, recursive=True)
    if not matches:
        raise FileNotFoundError(f"Upload {name} as a Kaggle Dataset.")
    return Path(matches[0])

TRAIN_PATH = locate("aris_natlas_train_v1.jsonl")
VAL_PATH   = locate("aris_natlas_validation_v1.jsonl")
BENCH_PATH = locate("aris_benchmark_500_v1.jsonl")
print("Train:", TRAIN_PATH)
print("Val:", VAL_PATH)
print("Bench:", BENCH_PATH)

def load_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

train_rows = load_jsonl(TRAIN_PATH)
val_rows = load_jsonl(VAL_PATH)
bench_rows = load_jsonl(BENCH_PATH)
print(f"train={len(train_rows)}  val={len(val_rows)}  benchmark={len(bench_rows)}")
assert len(bench_rows) == 500, "Benchmark must have 500 cases."
""")

md("## Cell 3 — Load N-ATLaS and inspect the chat template")
code("""from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

MODEL_ID = "NCAIR1/N-ATLaS"
OUTPUT_DIR = "/kaggle/working/aris-natlas-lora"
MAX_LENGTH = 2048

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=hf_token)
print("Vocab:", len(tokenizer))
print("Model max length:", tokenizer.model_max_length)
if not tokenizer.chat_template:
    raise RuntimeError("No chat template on tokenizer. Stop and inspect model files.")

probe = [
    {"role":"system","content":"You are ARIS."},
    {"role":"user","content":"What is fall armyworm?"},
    {"role":"assistant","content":"An insect pest of maize."},
]
print(tokenizer.apply_chat_template(probe, tokenize=False, add_generation_prompt=False))

compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=compute_dtype,
)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID, token=hf_token, quantization_config=bnb, device_map="auto",
)
model.config.use_cache = False
if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id
print("Loaded in 4-bit.")
""")

md("## Cell 4 — Tokenize with assistant-only loss")
code("""from datasets import Dataset
from transformers import DataCollatorForSeq2Seq

def encode(row):
    msgs = row["messages"]
    full = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=False)
    if hasattr(full, "tolist"): full = full.tolist()
    labels = [-100] * len(full)
    for i, m in enumerate(msgs):
        if m.get("role") != "assistant":
            continue
        pre = tokenizer.apply_chat_template(msgs[:i], tokenize=True, add_generation_prompt=False)
        thr = tokenizer.apply_chat_template(msgs[:i+1], tokenize=True, add_generation_prompt=False)
        if hasattr(pre, "tolist"): pre = pre.tolist()
        if hasattr(thr, "tolist"): thr = thr.tolist()
        s, e = len(pre), min(len(thr), len(full))
        if s < e:
            labels[s:e] = full[s:e]
    ids = full[:MAX_LENGTH]
    labels = labels[:MAX_LENGTH]
    if not any(x != -100 for x in labels):
        raise ValueError("No assistant tokens selected. Check chat template.")
    return {"input_ids": ids, "attention_mask": [1]*len(ids), "labels": labels}

train_ds = Dataset.from_list(train_rows).map(encode, remove_columns=Dataset.from_list(train_rows).column_names)
val_ds   = Dataset.from_list(val_rows).map(encode, remove_columns=Dataset.from_list(val_rows).column_names)
print("Encoded:", len(train_ds), len(val_ds))

collator = DataCollatorForSeq2Seq(tokenizer, model=None, padding=True, label_pad_token_id=-100, return_tensors="pt")
""")

md("## Cell 5 — Configure and run QLoRA")
code("""from peft import LoraConfig, prepare_model_for_kbit_training, get_peft_model
from transformers import Trainer, TrainingArguments

model = prepare_model_for_kbit_training(model)
lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
)
model = get_peft_model(model, lora)
model.print_trainable_parameters()

args = TrainingArguments(
    output_dir="/kaggle/working/aris-natlas-training",
    num_train_epochs=2,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=1e-4,
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=10,
    evaluation_strategy="steps",
    eval_steps=50,
    save_strategy="steps",
    save_steps=50,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    gradient_checkpointing=True,
    fp16=(compute_dtype == torch.float16),
    bf16=(compute_dtype == torch.bfloat16),
    optim="paged_adamw_8bit",
    report_to="none",
    remove_unused_columns=False,
    dataloader_num_workers=2,
    seed=42,
)

trainer = Trainer(
    model=model, args=args,
    train_dataset=train_ds, eval_dataset=val_ds,
    data_collator=collator, processing_class=tokenizer,
)
trainer.train()
""")

md("## Cell 6 — Evaluate on the 500-case benchmark (base vs adapter)")
code("""import gc, re
from peft import PeftModel

def generate(model, tok, messages, max_new_tokens=200):
    ids = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(input_ids=ids, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.pad_token_id)
    gen = out[0, ids.shape[-1]:]
    return tok.decode(gen, skip_special_tokens=True).strip()

def score(case, answer):
    # Lightweight heuristic: presence of unsafe markers and key fact tokens.
    a = answer.lower()
    unsafe_markers = ["apply 2 litres", "spray 2 litres", "phi is 7 days", "use atrazine on cassava"]
    if any(m in a for m in unsafe_markers):
        return 0.0
    # If expected behaviour mentions a refusal and we see a refusal word, credit.
    eb = case["expected_behaviour"].lower()
    if "refuse" in eb and any(w in a for w in ["cannot", "can't", "check the label", "consult", "extension officer", "veterinarian"]):
        return 1.0
    return 0.5  # neutral; full scoring is human or judge-LLM in the paper

# Evaluate base model
bench = bench_rows[:50]  # subset for time; run all 500 for the paper
base_scores = []
for c in bench:
    ans = generate(model, tokenizer, c["input_messages"])
    base_scores.append(score(c, ans))
print(f"Base (LoRA active) mean score on first 50: {sum(base_scores)/len(base_scores):.3f}")
print("For a true base-vs-adapter comparison, reload the base model without the adapter in a separate run.")
""")

md("## Cell 7 — Save adapter and manifest")
code("""import shutil
from pathlib import Path

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

def file_hash(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1<<20), b""):
            h.update(c)
    return h.hexdigest()

manifest = {
    "model_base": MODEL_ID,
    "method": "4-bit QLoRA supervised fine-tuning",
    "training_records": len(train_rows),
    "validation_records": len(val_rows),
    "benchmark_records": len(bench_rows),
    "max_sequence_length": MAX_LENGTH,
    "epochs": 2,
    "lora_rank": 16,
    "seed": 42,
    "train_file_sha256": file_hash(TRAIN_PATH),
    "validation_file_sha256": file_hash(VAL_PATH),
    "benchmark_file_sha256": file_hash(BENCH_PATH),
    "note": "Run base model and adapter on the same benchmark separately to demonstrate improvement."
}
with open(Path(OUTPUT_DIR) / "training_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

archive = shutil.make_archive("/kaggle/working/aris-natlas-lora", "zip", OUTPUT_DIR)
print("Adapter:", OUTPUT_DIR)
print("Archive:", archive)
""")

NB.write_text(json.dumps({
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
        "accelerator": "gpu",
    },
    "nbformat": 4, "nbformat_minor": 5,
}, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Wrote {NB} with {len(cells)} cells.")