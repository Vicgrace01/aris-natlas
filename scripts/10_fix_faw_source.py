"""Replace FAW-002's FAO source with IITA (primary FAW authority for Africa)."""
import json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "processed" / "aris_fact_ledger_v1.jsonl"
MANIFEST = ROOT / "build" / "verified_release_manifest_v1.json"

rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
changed = 0
for r in rows:
    if r["fact_id"] == "FAW-002":
        r["source_name"] = "IITA"
        r["source_url"] = "https://www.iita.org/crops/maize/"
        changed += 1

LEDGER.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

man = json.loads(MANIFEST.read_text(encoding="utf-8"))
man["fact_ledger"]["sha256"] = sha(LEDGER)
MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Changed {changed} record.")
print(f"New ledger SHA256: {sha(LEDGER)}")