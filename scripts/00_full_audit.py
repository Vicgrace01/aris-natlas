import os
import json
import hashlib
from pathlib import Path
from collections import Counter

ROOT = Path(r"C:\Projects\ARIS-nATLAS")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "build" / "initial_audit.txt"
OUT.parent.mkdir(parents=True, exist_ok=True)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect_jsonl(path):
    rows = []
    errors = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                errors.append(f"Line {line_no}: {e}")

    print(f"\n{'=' * 85}")
    print(f"FILE: {path.relative_to(ROOT)}")
    print(f"SIZE: {path.stat().st_size:,} bytes")
    print(f"SHA256: {sha256(path)}")
    print(f"VALID JSON RECORDS: {len(rows):,}")
    print(f"PARSE ERRORS: {len(errors)}")

    if errors:
        for error in errors[:10]:
            print("  ERROR:", error)

    keys = Counter()
    roles = Counter()
    languages = Counter()
    row_lengths = Counter()
    system_stats = Counter()
    embedded_prompt_count = 0
    samples = []

    for row in rows:
        if isinstance(row, dict):
            keys.update(row.keys())
            messages = row.get("messages")
            if isinstance(messages, list):
                row_lengths[len(messages)] += 1
                for msg in messages:
                    if isinstance(msg, dict):
                        roles[msg.get("role", "<missing>")] += 1
                        content = str(msg.get("content", ""))
                        if msg.get("role") == "system":
                            system_stats["explicit_system_messages"] += 1
                        if "You are ARIS" in content or "You are an AI" in content:
                            if msg.get("role") != "system":
                                embedded_prompt_count += 1
                if len(samples) < 3:
                    samples.append(row)
            else:
                roles["NO messages list"] += 1
                if len(samples) < 3:
                    samples.append(row)
        else:
            roles[f"non-dict:{type(row).__name__}"] += 1

    print("\nTOP-LEVEL KEYS:")
    for key, count in keys.most_common():
        print(f"  {key}: {count:,} records")

    print("\nMESSAGE ROLES:")
    for role, count in roles.most_common():
        print(f"  {role}: {count:,}")

    print("\nMESSAGES PER RECORD:")
    for count, freq in sorted(row_lengths.items()):
        print(f"  {count} messages: {freq:,} records")

    print(f"\nEXPLICIT SYSTEM MESSAGES: {system_stats['explicit_system_messages']:,}")
    print(f"PROMPT-LIKE TEXT OUTSIDE SYSTEM ROLE: {embedded_prompt_count:,}")

    print("\nFIRST THREE RECORDS (FULL):")
    for i, sample in enumerate(samples, 1):
        print(f"\n--- RECORD {i} ---")
        print(json.dumps(sample, ensure_ascii=False, indent=2))

    return {
        "file": str(path.relative_to(ROOT)),
        "records": len(rows),
        "sha256": sha256(path),
        "parse_errors": errors,
        "keys": dict(keys),
        "roles": dict(roles),
        "message_lengths": dict(row_lengths),
        "explicit_system_messages": system_stats["explicit_system_messages"],
        "embedded_prompt_count": embedded_prompt_count,
        "samples": samples,
    }

print("ARIS-N-ATLAS INITIAL DATA AUDIT")
print("Project:", ROOT)
print("Python:", os.sys.version.split()[0])
print("Raw folder exists:", RAW.exists())

results = []
if not RAW.exists():
    print("\nERROR: data\\raw folder does not exist.")
else:
    files = sorted(RAW.glob("*.jsonl"))
    print("JSONL files found:", len(files))
    for path in files:
        try:
            results.append(inspect_jsonl(path))
        except Exception as e:
            print(f"\nFAILED TO INSPECT {path.name}: {type(e).__name__}: {e}")

    expected = [
        "legacy_train.jsonl",
        "legacy_val.jsonl",
        "legacy_eval_frozen.jsonl",
    ]
    print("\nEXPECTED FILE CHECK:")
    for name in expected:
        print(f"  {name}: {'FOUND' if (RAW / name).exists() else 'MISSING'}")

    print("\nOTHER PROJECT FILES:")
    for folder in ["scripts", "configs", "data/facts", "data/curated",
                   "data/generated", "data/eval", "build", "docs"]:
        p = ROOT / folder
        print(f"\n[{folder}] {'EXISTS' if p.exists() else 'MISSING'}")
        if p.exists():
            items = list(p.rglob("*"))
            files_here = [x for x in items if x.is_file()]
            for item in files_here[:30]:
                print(f"  {item.relative_to(ROOT)} ({item.stat().st_size:,} bytes)")
            if len(files_here) > 30:
                print(f"  ... and {len(files_here) - 30} more files")

report = {
    "project": str(ROOT),
    "results": results,
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n\nAUDIT REPORT SAVED TO: {OUT}")
print("No source datasets were modified.")
