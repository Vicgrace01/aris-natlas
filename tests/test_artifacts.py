"""
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
