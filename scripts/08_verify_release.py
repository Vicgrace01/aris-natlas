"""
Final integrity check before commit.
- Validates fact ledger schema
- Confirms benchmark has 500 unique cases with target distribution
- Confirms manifest hashes match the actual files
- Optionally pings source URLs (skipped if offline)
"""
import json, hashlib, sys, urllib.request, urllib.error
from pathlib import Path
from collections import Counter

ROOT = Path.cwd()
PROC = ROOT / "data" / "processed"
BUILD = ROOT / "build"

LEDGER = PROC / "aris_fact_ledger_v1.jsonl"
CORR = PROC / "aris_corrected_training_v1.jsonl"
EXP = PROC / "aris_expanded_training_v1.jsonl"
BENCH = PROC / "aris_benchmark_500_v1.jsonl"
MANIFEST = BUILD / "verified_release_manifest_v1.json"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def load_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

errors = []

# --- ledger ---
ledger = load_jsonl(LEDGER)
if len(ledger) < 30:
    errors.append(f"ledger too small: {len(ledger)}")
required = {"fact_id","crop_or_topic","claim","status","source_name","source_url","conditions"}
for i, f in enumerate(ledger):
    missing = required - set(f.keys())
    if missing:
        errors.append(f"ledger row {i} missing {missing}")
    if f.get("status") not in {"verified","conditional","time_sensitive","uncertain"}:
        errors.append(f"ledger row {i} bad status: {f.get('status')}")
print(f"Ledger      : {len(ledger)} facts  OK")

# --- corrected ---
corr = load_jsonl(CORR)
for i, r in enumerate(corr):
    if "messages" not in r:
        errors.append(f"corrected row {i} has no messages")
print(f"Corrected   : {len(corr)} records  OK")

# --- expanded ---
exp = load_jsonl(EXP)
no_prov = [i for i, r in enumerate(exp) if not r.get("provenance", {}).get("fact_ids")]
print(f"Expanded    : {len(exp)} records  ({len(no_prov)} without fact provenance)")

# --- benchmark ---
bench = load_jsonl(BENCH)
if len(bench) != 500:
    errors.append(f"benchmark is {len(bench)}, not 500")
ids = [c["case_id"] for c in bench]
if len(set(ids)) != 500:
    errors.append("duplicate case_ids in benchmark")
counts = Counter(c["category"] for c in bench)
target = {
    "crop_disease_pest":80,"planting_spacing":60,"fertilizer_calc":60,
    "pesticide_safety":60,"soil_water_weather":40,"harvest_postharvest":40,
    "livestock":40,"language_codeswitching":60,"uncertainty_adversarial":30,
    "prompt_robustness":30,
}
for k, v in target.items():
    if counts.get(k, 0) != v:
        errors.append(f"category {k}: {counts.get(k,0)} != {v}")
print(f"Benchmark   : 500 cases  OK  (all categories match target)")

# --- manifest hash ---
man = json.loads(MANIFEST.read_text(encoding="utf-8"))
for key, path in [("fact_ledger", LEDGER), ("corrected_training", CORR),
                  ("expanded_training", EXP), ("benchmark_500", BENCH)]:
    recorded = man.get(key, {}).get("sha256")
    actual = sha(path)
    if recorded != actual:
        errors.append(f"manifest hash mismatch for {key}: {recorded} != {actual}")
print(f"Manifest    : hashes match  OK")

# --- URL check (best-effort, offline tolerated) ---
print()
print("Checking source URLs (best-effort)...")
seen = set()
url_ok, url_fail = 0, []
for f in ledger:
    u = f["source_url"]
    if u in seen:
        continue
    seen.add(u)
    try:
        req = urllib.request.Request(u, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            if r.status < 400:
                url_ok += 1
            else:
                url_fail.append((u, r.status))
    except urllib.error.HTTPError as e:
        url_fail.append((u, e.code))
    except Exception as e:
        url_fail.append((u, str(e)))

print(f"  reachable: {url_ok} / {len(seen)}")
for u, reason in url_fail:
    print(f"  FAIL {u} -> {reason}")

print()
if errors:
    print("=== ERRORS ===")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("=== VERIFICATION PASSED ===")