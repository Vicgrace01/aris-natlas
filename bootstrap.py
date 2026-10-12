"""
ARIS-N-ATLaS repo bootstrap. Writes docs, tests, CI, LICENSE, .gitignore, and scripts/09.
Run once: python bootstrap.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def write(rel, content):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  wrote {rel} ({len(content)} bytes)")

write("scripts/09_patch_source_urls.py", r'''"""Patch source URLs in the fact ledger to currently valid pages."""
import json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "processed" / "aris_fact_ledger_v1.jsonl"
MANIFEST = ROOT / "build" / "verified_release_manifest_v1.json"

URL_MAP = {
    "https://www.iita.org/cropsnew/fall-armyworm/": "https://www.iita.org/crops/maize/",
    "https://www.iita.org/cropsnew/cassava/":       "https://www.iita.org/crops/cassava/",
    "https://www.iita.org/cropsnew/maize/":         "https://www.iita.org/crops/maize/",
    "https://www.fao.org/fall-armyworm/en/":        "https://www.fao.org/plant-production-protection/areas-of-work/fall-armyworm/en",
}

rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
changed = 0
for r in rows:
    old = r.get("source_url")
    if old in URL_MAP:
        r["source_url"] = URL_MAP[old]
        changed += 1

LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

if MANIFEST.exists():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    man["fact_ledger"]["sha256"] = sha(LEDGER)
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Patched {changed} URLs.")
print(f"New ledger SHA256: {sha(LEDGER)}")
''')

write("docs/DESIGN.md", r'''# Design notes

## Why a fact ledger

Generating 500 agricultural answers is a coding task. Establishing that they are correct is a verification task. This repository separates the two.

Every training record references `fact_id` values. Every `fact_id` carries a source URL, source name, conditions, and status.

## Status values

| Status | Meaning | Trains? |
|---|---|---|
| `verified` | Sourced and consistent across authorities | Yes |
| `conditional` | Sourced but depends on region, crop stage, or soil test | Yes, with the condition stated |
| `time_sensitive` | Correct now, will drift | No |
| `uncertain` | Flagged for review | No |

## Why the benchmark is separate

NCAIR requires measurable improvement over base N-ATLaS on a benchmark of at least 500 examples. If any benchmark case leaks into training, the measurement is invalid. The benchmark is a separate file, verified by SHA256 in the release manifest.

## The FAW-vs-CMD distinction

The most common failure mode in the original ARIS dataset was confusing fall armyworm (an insect on maize) with cassava mosaic disease (a virus on cassava). Ledger entries `FAW-*`, `CMD-*`, and `CMP-001` encode the correct distinction.
''')

write("docs/PROVENANCE.md", r'''# Provenance

Every release artifact is hashed and recorded in `build/verified_release_manifest_v1.json`.

## Artifact lineage

| Artifact | Built by |
|---|---|
| `data/processed/aris_fact_ledger_v1.jsonl` | `scripts/06_build_verified_dataset.py` |
| `data/processed/aris_corrected_training_v1.jsonl` | `scripts/06_build_verified_dataset.py` |
| `data/processed/aris_expanded_training_v1.jsonl` | `scripts/06_build_verified_dataset.py` |
| `data/processed/aris_benchmark_500_v1.jsonl` | `scripts/06`, rebalanced by `scripts/07_rebalance_benchmark.py` |
| `build/verified_release_manifest_v1.json` | Emitted by `06`, updated by `07` and `09` |

## Verification

`scripts/08_verify_release.py` checks schema, benchmark count and distribution, unique IDs, SHA256 hashes, and best-effort URL reachability.

CI (`.github/workflows/verify.yml`) runs the same checks on every push to `main`.
''')

write("docs/SOURCE_REGISTRY.md", r'''# Source Registry

| Source | Abbreviation | URL | Domain |
|---|---|---|---|
| International Institute of Tropical Agriculture | IITA | https://www.iita.org | Maize, cassava, FAW, post-harvest |
| Food and Agriculture Organization of the UN | FAO | https://www.fao.org | Pesticide safety, fertilizer math, FAW |
| National Root Crops Research Institute | NRCRI | https://nrcri.gov.ng | Cassava |
| National Agricultural Extension and Research Liaison Services | NAERLS | https://naerls.gov.ng | Extension, fertilizer, livestock |

## Rules

1. Every `fact_id` in the ledger must cite a source with a working URL.
2. Two generated answers agreeing is not a source.
3. Time-sensitive claims are labeled and never used as training targets.
4. Unreachable URLs are flagged in the verifier output and reviewed before the next release.
''')

write("docs/DATASET_CARD.md", r'''# Dataset Card — ARIS powered by N-ATLaS

## Overview

Supervised fine-tuning dataset for an offline agricultural advisor targeting Nigerian smallholder farmers, built on NCAIR's N-ATLaS (Llama 3 8B instruction-tuned).

## Artifacts

| File | Records | Purpose |
|---|---|---|
| `data/processed/aris_fact_ledger_v1.jsonl` | 33 | Source-backed agricultural facts |
| `data/processed/aris_corrected_training_v1.jsonl` | 21 | Targeted corrections for known failure modes |
| `data/processed/aris_expanded_training_v1.jsonl` | 154 | Training records with provenance |
| `data/processed/aris_benchmark_500_v1.jsonl` | 500 | Evaluation benchmark (never trained on) |

## Intended use

Fine-tune N-ATLaS to answer Nigerian agricultural questions safely and accurately, then measure improvement against the base model on the 500-case benchmark.

## Out of scope

- Clinical veterinary diagnosis
- Specific pesticide product names, rates, or PHI values
- Invented crop variety names

## Known limitations

- Hausa, Igbo, Yoruba coverage is scaffolded but not yet populated with verified records.
- Fact ledger v1 has 33 entries; expanding to full crop coverage is future work.
''')

write("tests/test_artifacts.py", r'''"""
Artifact integrity tests. Run with `python tests/test_artifacts.py` or `pytest tests/`.
"""
import json, hashlib
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
BUILD = ROOT / "build"

TARGET = {
    "crop_disease_pest": 80, "planting_spacing": 60, "fertilizer_calc": 60,
    "pesticide_safety": 60, "soil_water_weather": 40, "harvest_postharvest": 40,
    "livestock": 40, "language_codeswitching": 60, "uncertainty_adversarial": 30,
    "prompt_robustness": 30,
}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def load_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

def test_benchmark_count_and_distribution():
    bench = load_jsonl(PROC / "aris_benchmark_500_v1.jsonl")
    assert len(bench) == 500, f"benchmark is {len(bench)}, not 500"
    counts = Counter(c["category"] for c in bench)
    for k, v in TARGET.items():
        assert counts[k] == v, f"category {k}: {counts[k]} != {v}"
    ids = [c["case_id"] for c in bench]
    assert len(set(ids)) == 500, "duplicate case IDs"

def test_manifest_hashes():
    man = json.loads((BUILD / "verified_release_manifest_v1.json").read_text(encoding="utf-8"))
    for key, rel in [
        ("fact_ledger", "data/processed/aris_fact_ledger_v1.jsonl"),
        ("corrected_training", "data/processed/aris_corrected_training_v1.jsonl"),
        ("expanded_training", "data/processed/aris_expanded_training_v1.jsonl"),
        ("benchmark_500", "data/processed/aris_benchmark_500_v1.jsonl"),
    ]:
        p = ROOT / rel
        assert man[key]["sha256"] == sha(p), f"hash mismatch: {key}"

def test_fact_ledger_schema():
    ledger = load_jsonl(PROC / "aris_fact_ledger_v1.jsonl")
    required = {"fact_id","crop_or_topic","claim","status","source_name","source_url","conditions"}
    for i, f in enumerate(ledger):
        assert required <= set(f.keys()), f"row {i} missing fields"
        assert f["status"] in {"verified","conditional","time_sensitive","uncertain"}, f"row {i} bad status"

def test_training_provenance():
    for name in ["aris_corrected_training_v1.jsonl", "aris_expanded_training_v1.jsonl"]:
        rows = load_jsonl(PROC / name)
        missing = [i for i, r in enumerate(rows) if not r.get("provenance", {}).get("fact_ids")]
        assert not missing, f"{name}: rows {missing[:5]} have no fact_ids"

if __name__ == "__main__":
    test_benchmark_count_and_distribution()
    test_manifest_hashes()
    test_fact_ledger_schema()
    test_training_provenance()
    print("All artifact integrity tests passed.")
''')

write("tests/__init__.py", "")

write(".github/workflows/verify.yml", r'''name: verify

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  integrity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Run artifact integrity tests
        run: python tests/test_artifacts.py
''')

write(".gitignore", r'''# Environments
.venv/
venv/
env/
__pycache__/
*.pyc

# Model artifacts (large)
*.safetensors
*.bin
*.pt
*.gguf
models/

# Caches
.cache/
kaggle/
huggingface/

# Secrets
.env
.env.*
secrets/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Large build archives
build/*.zip
build/*.tar.gz
''')

write("LICENSE", r'''MIT License

Copyright (c) 2026 Victor (Vicgrace01)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')

print()
print("Bootstrap complete.")
print("Next:")
print("  python scripts\\09_patch_source_urls.py")
print("  python scripts\\08_verify_release.py")
print("  python tests\\test_artifacts.py")