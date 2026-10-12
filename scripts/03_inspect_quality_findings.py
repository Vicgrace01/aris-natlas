import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"

FILES = {
    "train": DATA / "ARIS_V10_FINAL_DATASET_V5 (1).jsonl",
    "validation": DATA / "ARIS_V10_VAL_DATASET.jsonl",
    "evaluation": DATA / "ARIS_V10_EVAL_FROZEN_V3.jsonl",
}

def load_records(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def messages_of(record):
    return record.get("messages", [])

def content(message):
    value = message.get("content", "")
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False)

def short(value, limit=650):
    value = " ".join(str(value).split())
    return value if len(value) <= limit else value[:limit] + " [...]"

def system_text(record):
    return "\n".join(
        content(m) for m in messages_of(record)
        if m.get("role") == "system"
    )

def user_texts(record):
    return [
        content(m) for m in messages_of(record)
        if m.get("role") == "user" and content(m)
    ]

def assistant_texts(record):
    return [
        content(m) for m in messages_of(record)
        if m.get("role") == "assistant" and content(m)
    ]

def conversation_key(record):
    # Compare complete conversations while ignoring system-prompt differences.
    payload = [
        {"role": m.get("role"), "content": content(m)}
        for m in messages_of(record)
        if m.get("role") != "system"
    ]
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)

records = {name: load_records(path) for name, path in FILES.items()}

print("=" * 78)
print("ARIS QUALITY FINDINGS: CONTENT INSPECTION")
print("Read-only. No source data will be modified.")
print("=" * 78)

# 1. Print actual system prompt variants.
print("\n1. ACTUAL TRAINING SYSTEM PROMPT VARIANTS")
variants = defaultdict(list)
for i, record in enumerate(records["train"], 1):
    prompt = system_text(record)
    if prompt:
        variants[prompt].append(i)

print(f"Distinct non-empty variants: {len(variants)}")
for number, (prompt, indices) in enumerate(
    sorted(variants.items(), key=lambda item: len(item[1]), reverse=True), 1
):
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    print(f"\n--- Variant {number}: {len(indices)} records; SHA256 prefix={digest}")
    print(f"Example record indices: {indices[:12]}")
    print(short(prompt, 2400))

# 2. Largest exact duplicate conversation groups.
print("\n\n2. EXACT DUPLICATE CONVERSATIONS IN TRAINING")
groups = defaultdict(list)
for i, record in enumerate(records["train"], 1):
    groups[conversation_key(record)].append((i, record))

duplicates = [
    items for items in groups.values()
    if len(items) > 1
]
duplicates.sort(key=lambda items: len(items), reverse=True)

print(f"Duplicate groups: {len(duplicates)}")
print(f"Records belonging to those groups: {sum(len(g) for g in duplicates)}")

for number, group in enumerate(duplicates[:12], 1):
    sample = group[0][1]
    print(f"\n--- Group {number}: {len(group)} copies; record indices={[x[0] for x in group[:20]]}")
    users = user_texts(sample)
    assistants = assistant_texts(sample)
    print("Last/first user message:", short(users[0] if users else "(none)"))
    print("First assistant answer:", short(assistants[0] if assistants else "(none)"))

# 3. Shared user prompts across train and validation.
print("\n\n3. USER PROMPTS SHARED BY TRAIN AND VALIDATION")
def prompt_index(dataset):
    index = defaultdict(list)
    for i, record in enumerate(dataset, 1):
        for message in messages_of(record):
            if message.get("role") == "user":
                value = content(message)
                if value:
                    index[value].append((i, record))
    return index

train_prompts = prompt_index(records["train"])
val_prompts = prompt_index(records["validation"])
shared = sorted(set(train_prompts) & set(val_prompts))

print(f"Distinct exact user prompts shared: {len(shared)}")
for number, prompt in enumerate(shared, 1):
    train_hits = train_prompts[prompt]
    val_hits = val_prompts[prompt]
    print(f"\n--- Shared prompt {number}")
    print(f"Train occurrences: {len(train_hits)}; validation occurrences: {len(val_hits)}")
    print("User prompt:", short(prompt, 450))

    for label, hits in (("TRAIN", train_hits[:2]), ("VALIDATION", val_hits[:2])):
        for record_number, record in hits:
            answers = assistant_texts(record)
            print(f"  {label} record {record_number}:")
            print("    First assistant answer:", short(answers[0] if answers else "(none)", 450))

# 4. Confirm evaluation records remain rubric-like.
print("\n\n4. FROZEN EVALUATION FILE STRUCTURE")
evaluation = records["evaluation"]
print(f"Records: {len(evaluation)}")
if evaluation:
    print("First record keys:", list(evaluation[0].keys()))
    print("First record fields are not being used to create training examples.")

print("\nINSPECTION COMPLETE. No files were changed.")
