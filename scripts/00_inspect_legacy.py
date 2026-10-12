"""Inspect the ARIS v10 legacy JSONL datasets."""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    ROOT / "data" / "raw" / "legacy_train.jsonl",
    ROOT / "data" / "raw" / "legacy_val.jsonl",
    ROOT / "data" / "raw" / "legacy_eval_frozen.jsonl",
]

SYS_MARKERS = ["You are ARIS", "No internet access", "No camera",
               "No live market prices", "No ability to prescribe",
               "verified Nigerian agricultural"]

def has_system(content):
    return sum(1 for m in SYS_MARKERS if m in content) >= 2

def main():
    for path in FILES:
        if not path.exists():
            print(f"\nMISSING: {path}")
            continue
        print("\n" + "="*60)
        print(f"FILE: {path.name}")
        print("="*60)

        rows, bad = [], 0
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1

        print(f"Total rows: {len(rows)}")
        print(f"Malformed: {bad}")
        if not rows:
            continue

        print(f"Top-level keys in row 1: {list(rows[0].keys())}")

        role_counter = Counter()
        embedded_sys = 0
        for r in rows:
            for m in r.get("messages", []):
                role_counter[m.get("role")] += 1
                if has_system(m.get("content", "")):
                    embedded_sys += 1
        print(f"Roles: {dict(role_counter)}")
        print(f"Turns with embedded system prompt: {embedded_sys}")

        print("\nSample row 1 (truncated):")
        print(json.dumps(rows[0], ensure_ascii=False)[:800])
        print()

if __name__ == "__main__":
    main()
