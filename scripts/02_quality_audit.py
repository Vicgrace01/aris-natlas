import json
import re
import hashlib
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(r"C:\Projects\ARIS-nATLAS")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "build"
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    "train": RAW / "legacy_train.jsonl",
    "validation": RAW / "legacy_val.jsonl",
    "evaluation": RAW / "legacy_eval_frozen.jsonl",
}

def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(
                    f"{path.name}, line {line_no}: {exc}"
                ) from exc
    return rows

def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip().casefold()

def digest(value):
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def messages_of(row):
    return row.get("messages", []) if isinstance(row, dict) else []

def conversation_key(row):
    # Exclude system messages so different prompt formatting
    # does not conceal otherwise identical conversations.
    msgs = messages_of(row)
    relevant = [
        {"role": m.get("role"), "content": norm(m.get("content", ""))}
        for m in msgs
        if isinstance(m, dict) and m.get("role") != "system"
    ]
    return digest(relevant) if relevant else None

def analyse(name, rows):
    role_counts = Counter()
    lengths = Counter()
    system_hashes = Counter()
    system_variants = {}
    issues = Counter()
    sequences = Counter()
    user_questions = Counter()
    question_answers = defaultdict(set)
    suspicious = []
    examples = []

    for i, row in enumerate(rows, 1):
        msgs = messages_of(row)
        lengths[len(msgs)] += 1

        if not isinstance(row, dict) or not isinstance(msgs, list):
            issues["invalid_record_or_messages"] += 1
            continue

        roles = []
        for m in msgs:
            if not isinstance(m, dict):
                issues["invalid_message_object"] += 1
                continue

            role = str(m.get("role", "<missing>"))
            content = str(m.get("content", ""))
            roles.append(role)
            role_counts[role] += 1

            if not content.strip():
                issues["empty_message_content"] += 1

            if role == "system":
                h = hashlib.sha256(
                    norm(content).encode("utf-8")
                ).hexdigest()[:16]
                system_hashes[h] += 1
                system_variants.setdefault(h, content[:180])

            if "\ufffd" in content:
                issues["replacement_character"] += 1

            if "╫" in content:
                issues["suspicious_cassava_spacing_symbol"] += 1

            if re.search(
                r"\b(CVR240|MAIZE\s*158193)\b",
                content, re.I
            ):
                issues["known_suspicious_variety_strings"] += 1

            if re.search(
                r"TODO|INSERT HERE|PLACEHOLDER|<SOURCE",
                content, re.I
            ):
                issues["possible_placeholder_text"] += 1

        sequences[" -> ".join(roles)] += 1

        users = [
            norm(m.get("content", ""))
            for m in msgs
            if isinstance(m, dict) and m.get("role") == "user"
        ]
        answers = [
            norm(m.get("content", ""))
            for m in msgs
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]

        for q in users:
            if q:
                user_questions[q] += 1
                for a in answers:
                    if a:
                        question_answers[q].add(a)

        if len(suspicious) < 20:
            hits = []
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                c = str(m.get("content", ""))
                if (
                    "\ufffd" in c
                    or "╫" in c
                    or re.search(
                        r"\b(CVR240|MAIZE\s*158193)\b", c, re.I
                    )
                ):
                    hits.append({
                        "role": m.get("role"),
                        "content_excerpt": c[:350]
                    })
            if hits:
                suspicious.append({
                    "record_index": i,
                    "findings": hits
                })

    conflicting_candidates = []
    for question, answers in question_answers.items():
        if len(answers) > 1 and user_questions[question] > 1:
            conflicting_candidates.append({
                "question": question[:300],
                "occurrences": user_questions[question],
                "distinct_assistant_responses": len(answers),
                "responses_sample": sorted(answers)[:3]
            })

    return {
        "records": len(rows),
        "role_counts": dict(role_counts),
        "message_lengths": dict(lengths),
        "role_sequences": dict(sequences.most_common(15)),
        "system_prompt_variants": dict(system_hashes),
        "system_prompt_examples": system_variants,
        "issues": dict(issues),
        "unique_user_questions": len(user_questions),
        "repeated_user_questions": sum(
            1 for n in user_questions.values() if n > 1
        ),
        "repeated_question_candidates": conflicting_candidates[:30],
        "suspicious_examples": suspicious,
    }

print("=" * 76)
print("ARIS-N-ATLAS DATA QUALITY AUDIT")
print("Original files will not be modified.")
print("=" * 76)

loaded = {}
for name, path in FILES.items():
    if not path.exists():
        print(f"MISSING: {path}")
        continue
    rows = load_jsonl(path)
    loaded[name] = rows
    print(f"\n{name.upper()}: {len(rows):,} records")
    print("SHA256:", hashlib.sha256(path.read_bytes()).hexdigest())

reports = {}
for name, rows in loaded.items():
    reports[name] = analyse(name, rows)
    r = reports[name]
    print(f"\n--- {name.upper()} QUALITY SUMMARY ---")
    print("Roles:", r["role_counts"])
    print("Message counts:", r["message_lengths"])
    print("Common role sequences:")
    for seq, count in r["role_sequences"].items():
        print(f"  {count:>5}  {seq}")
    print("Distinct system prompt variants:", len(r["system_prompt_variants"]))
    print("System prompt frequencies:", r["system_prompt_variants"])
    print("Automated warning counts:", r["issues"])
    print("Unique user questions:", r["unique_user_questions"])
    print("Repeated-question candidates:", len(r["repeated_question_candidates"]))

# Exact conversation duplicates within each split and between splits.
keys_by_split = {}
for name, rows in loaded.items():
    mapping = defaultdict(list)
    for i, row in enumerate(rows, 1):
        key = conversation_key(row)
        if key:
            mapping[key].append(i)
    keys_by_split[name] = mapping

print("\n" + "=" * 76)
print("DUPLICATE AND CROSS-SPLIT CHECKS")
print("=" * 76)

duplicate_report = {}
for name, mapping in keys_by_split.items():
    groups = {
        key: indices for key, indices in mapping.items()
        if len(indices) > 1
    }
    duplicate_report[f"{name}_duplicate_groups"] = [
        {"record_indices": indices}
        for indices in list(groups.values())[:50]
    ]
    duplicate_report[f"{name}_duplicate_group_count"] = len(groups)
    print(
        f"{name}: {len(groups)} exact duplicate conversation groups"
    )

if "train" in keys_by_split and "validation" in keys_by_split:
    train_keys = set(keys_by_split["train"])
    val_keys = set(keys_by_split["validation"])
    overlap = train_keys & val_keys
    duplicate_report["train_validation_exact_overlap_count"] = len(overlap)
    duplicate_report["train_validation_overlap_examples"] = [
        {
            "train_indices": keys_by_split["train"][key],
            "validation_indices": keys_by_split["validation"][key],
        }
        for key in list(overlap)[:50]
    ]
    print("Exact train-validation conversation overlaps:", len(overlap))

# Repeated user prompts across train and validation, even when
# the surrounding conversations differ.
if "train" in loaded and "validation" in loaded:
    def prompt_index(rows):
        result = defaultdict(list)
        for i, row in enumerate(rows, 1):
            for m in messages_of(row):
                if isinstance(m, dict) and m.get("role") == "user":
                    q = norm(m.get("content", ""))
                    if q:
                        result[q].append(i)
        return result

    tq = prompt_index(loaded["train"])
    vq = prompt_index(loaded["validation"])
    shared = set(tq) & set(vq)
    duplicate_report["shared_user_prompt_count"] = len(shared)
    duplicate_report["shared_user_prompt_examples"] = [
        {
            "question": q[:250],
            "train_indices": tq[q][:10],
            "validation_indices": vq[q][:10],
        }
        for q in list(shared)[:50]
    ]
    print("Exact user prompts shared across train and validation:", len(shared))

report = {
    "files": {
        name: {
            "path": str(FILES[name]),
            "sha256": hashlib.sha256(FILES[name].read_bytes()).hexdigest(),
        }
        for name in loaded
    },
    "quality": reports,
    "duplicates": duplicate_report,
    "note": (
        "Automated flags are candidates for human review, not proof "
        "that a record is wrong. No source data was changed."
    )
}

out_path = OUT / "02_quality_audit.json"
out_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\nFULL REPORT:", out_path)
print("AUDIT COMPLETE. Original datasets remain unchanged.")
