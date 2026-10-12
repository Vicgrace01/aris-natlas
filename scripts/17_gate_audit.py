"""
Self-compliance audit. Fails loudly if any required artifact is missing or
malformed. Run this before every push.
"""
import json, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
BUILD = ROOT / "build"

checks = []
def check(label, condition, detail=""):
    checks.append(("[PASS]" if condition else "[FAIL]", label, detail))

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

# Required files
required = [
    ("data/processed/aris_fact_ledger_v1.jsonl", "fact ledger"),
    ("data/processed/aris_corrected_training_v1.jsonl", "corrected training"),
    ("data/processed/aris_expanded_training_v1.jsonl", "expanded training"),
    ("data/processed/aris_benchmark_500_v1.jsonl", "500-case benchmark"),
    ("data/processed/aris_redteam_battery_v1.jsonl", "red-team battery"),
    ("data/processed/aris_natlas_train_v1.jsonl", "training release"),
    ("data/processed/aris_natlas_validation_v1.jsonl", "validation release"),
    ("build/verified_release_manifest_v1.json", "release manifest"),
    ("REPORT.md", "technical report"),
    ("README.md", "readme"),
    ("docs/DESIGN.md", "design doc"),
    ("docs/DATASET_CARD.md", "dataset card"),
    ("docs/PROVENANCE.md", "provenance doc"),
    ("docs/SOURCE_REGISTRY.md", "source registry"),
    ("docs/REPRODUCE.md", "reproduce instructions"),
    ("tests/test_artifacts.py", "integrity tests"),
    (".github/workflows/verify.yml", "CI workflow"),
]
for path, label in required:
    check(f"{label}", (ROOT / path).exists(), path)

# Benchmark invariants
BENCH = PROC / "aris_benchmark_500_v1.jsonl"
if BENCH.exists():
    rows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    check("benchmark has exactly 500 cases", len(rows) == 500, f"got {len(rows)}")
    ids = [r["case_id"] for r in rows]
    check("benchmark case_ids unique", len(set(ids)) == 500)
    TARGET = {
        "crop_disease_pest": 80, "planting_spacing": 60, "fertilizer_calc": 60,
        "pesticide_safety": 60, "soil_water_weather": 40, "harvest_postharvest": 40,
        "livestock": 40, "language_codeswitching": 60, "uncertainty_adversarial": 30,
        "prompt_robustness": 30,
    }
    from collections import Counter
    counts = Counter(r["category"] for r in rows)
    for cat, target in TARGET.items():
        check(f"benchmark {cat} == {target}", counts.get(cat, 0) == target,
              f"got {counts.get(cat, 0)}")

# Fact ledger schema
LEDGER = PROC / "aris_fact_ledger_v1.jsonl"
if LEDGER.exists():
    facts = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    required_fields = {"fact_id", "crop_or_topic", "claim", "status",
                       "source_name", "source_url", "conditions"}
    ok = all(required_fields <= set(f.keys()) for f in facts)
    check("fact ledger schema valid", ok, f"{len(facts)} records")
    valid_status = {"verified", "conditional", "time_sensitive", "uncertain"}
    bad = [f["fact_id"] for f in facts if f["status"] not in valid_status]
    check("fact ledger statuses valid", not bad, f"bad: {bad[:3]}")

# Manifest hash matching
MANIFEST = BUILD / "verified_release_manifest_v1.json"
if MANIFEST.exists():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key, path in [
        ("fact_ledger", PROC / "aris_fact_ledger_v1.jsonl"),
        ("corrected_training", PROC / "aris_corrected_training_v1.jsonl"),
        ("expanded_training", PROC / "aris_expanded_training_v1.jsonl"),
        ("benchmark_500", PROC / "aris_benchmark_500_v1.jsonl"),
    ]:
        if key in man and path.exists():
            check(f"manifest hash {key}",
                  man[key].get("sha256") == sha(path),
                  "hash mismatch")

# REPORT.md sections
REPORT = ROOT / "REPORT.md"
if REPORT.exists():
    text = REPORT.read_text(encoding="utf-8")
    for section in ["## Executive summary", "## The problem", "## Design decisions",
                    "## Model provenance", "## Constraints",
                    "## Data verification methodology",
                    "## Benchmark methodology", "## Limitations",
                    "## How to reproduce"]:
        check(f"REPORT has '{section}'", section in text)

# Git attributes lock (no CRLF normalization)
GA = ROOT / ".gitattributes"
if GA.exists():
    text = GA.read_text(encoding="utf-8")
    check(".gitattributes locks line endings", "-text" in text or "text=auto" in text)

# Summary
passed = sum(1 for s, _, _ in checks if s == "[PASS]")
total = len(checks)
print(f"\n{'=' * 72}")
print(f"GATE AUDIT — {passed}/{total} checks passed")
print(f"{'=' * 72}")
for status, label, detail in checks:
    line = f"{status} {label}"
    if status == "[FAIL]" and detail:
        line += f"  -- {detail}"
    print(line)

BUILD.mkdir(exist_ok=True)
out = BUILD / "gate_audit_v1.json"
out.write_text(json.dumps({
    "passed": passed, "total": total,
    "checks": [{"status": s, "label": l, "detail": d} for s, l, d in checks],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {out}")

if passed != total:
    sys.exit(1)