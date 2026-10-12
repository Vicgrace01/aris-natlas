"""Patch source URLs in the fact ledger to currently valid pages."""
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
