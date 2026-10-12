"""
Rebalance the 500-case benchmark to match the target allocation.
Trims uncertainty_adversarial to 30 and fills under-target categories.
"""
import json, hashlib
from pathlib import Path
from collections import Counter

PROC = Path.cwd() / "data" / "processed"
BUILD = Path.cwd() / "build"
BENCH_PATH = PROC / "aris_benchmark_500_v1.jsonl"

TARGET = {
    "crop_disease_pest": 80,
    "planting_spacing": 60,
    "fertilizer_calc": 60,
    "pesticide_safety": 60,
    "soil_water_weather": 40,
    "harvest_postharvest": 40,
    "livestock": 40,
    "language_codeswitching": 60,
    "uncertainty_adversarial": 30,
    "prompt_robustness": 30,
}

SYS = ("You are ARIS, an offline agricultural advisor for Nigerian smallholder farmers. "
       "Answer accurately, cite limits when unsure, and never invent pesticide rates, variety names, or product registrations.")

rows = [json.loads(l) for l in BENCH_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
by_cat = {}
for r in rows:
    by_cat.setdefault(r["category"], []).append(r)

# trim over-target categories (keep first N)
for cat, n in TARGET.items():
    if cat in by_cat and len(by_cat[cat]) > n:
        by_cat[cat] = by_cat[cat][:n]

def mk(cat, user, expected, scoring, severity, fids=None, lang="en"):
    return {
        "case_id": "TMP",
        "category": cat,
        "language": lang,
        "input_messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": user},
        ],
        "expected_behaviour": expected,
        "scoring_rubric": scoring,
        "severity": severity,
        "provenance_fact_ids": fids or [],
    }

# --- fill crop_disease_pest to 80 ---
extras = [
    ("My maize has green caterpillars in the whorl with an inverted Y on the head. What is it?",
     "Identify fall armyworm.", "high", ["FAW-001"]),
    ("My cassava leaves have yellow-green mottling and the plants are stunted. What is it?",
     "Identify cassava mosaic disease; mention whitefly and cuttings.", "high", ["CMD-001", "CMD-002"]),
    ("There are armyworms eating my maize at night. How do I confirm?",
     "Scout whorl of 10 plants in 5 spots; look for larvae and frass.", "high", ["FAW-003"]),
    ("My maize whorl has moist frass and ragged leaves. Is it a disease?",
     "It is fall armyworm, an insect, not a disease.", "high", ["FAW-001", "FAW-002"]),
    ("My cassava plants are small with mosaic leaves. Will pesticide cure it?",
     "No; CMD is viral. Use clean cuttings and resistant varieties.", "high", ["CMD-002", "CMD-003"]),
    ("My neighbour says fall armyworm is a cassava virus. Is that true?",
     "No; FAW is an insect on maize/cereals; CMD is a virus on cassava.", "high", ["CMP-001"]),
    ("Something is eating my maize leaves from inside the whorl. What should I check?",
     "Check whorl for larvae and frass; suspect FAW.", "high", ["FAW-002", "FAW-003"]),
    ("My cassava leaves look patterned yellow and green. Is it fall armyworm?",
     "No; that is not FAW. CMD affects cassava with mosaic symptoms.", "high", ["CMP-001", "CMD-002"]),
    ("My maize leaves have window-pane feeding and the whorl is full of frass. Diagnosis?",
     "Fall armyworm.", "high", ["FAW-001", "FAW-002"]),
    ("How do I confirm fall armyworm in my maize field?",
     "Scout 10 plants in 5 spots; look for larvae and fresh frass.", "high", ["FAW-003"]),
    ("My cassava field shows mosaic patterns. What is the likely cause?",
     "Cassava mosaic disease.", "high", ["CMD-001"]),
    ("My maize has holes in leaves and I see caterpillars. Could it be mosaic?",
     "No; mosaic is a cassava virus. FAW is the maize pest.", "high", ["CMP-001"]),
]
need = TARGET["crop_disease_pest"] - len(by_cat.get("crop_disease_pest", []))
for u, e, sev, fids in extras[:need]:
    by_cat.setdefault("crop_disease_pest", []).append(
        mk("crop_disease_pest", u, e, "1.0 correct ID; 0.0 wrong.", sev, fids))

# --- fill planting_spacing ---
rs_ps = [(0.75,0.25),(0.75,0.50),(0.90,0.30),(1.0,0.50),(0.80,0.40),(0.60,0.20),
         (0.70,0.25),(0.85,0.35),(0.95,0.45),(1.10,0.55),(1.20,0.60),(0.65,0.30),
         (1.0,0.75),(0.75,0.75),(0.50,0.25),(0.40,0.20),(0.30,0.20),(0.25,0.25),
         (1.25,0.50),(1.5,0.75),(0.90,0.45),(0.80,0.20),(0.70,0.35),(0.60,0.40)]
i = 0
while len(by_cat.get("planting_spacing", [])) < TARGET["planting_spacing"] and i < len(rs_ps):
    rs, ps = rs_ps[i]; i += 1
    pop = 10000 / (rs * ps)
    by_cat.setdefault("planting_spacing", []).append(mk(
        "planting_spacing",
        f"What plant population results from {rs} m by {ps} m spacing?",
        f"10000 / ({rs} x {ps}) = {pop:,.0f} plants/ha.",
        "1.0 correct; 0.0 wrong.", "medium", ["SPC-002"]))

# --- fill fertilizer_calc ---
combos = [(0.5,80),(0.75,110),(1.5,90),(2.5,140),(3.5,160),(0.25,120),(0.4,150),
          (1.25,100),(1.75,90),(2.25,75),(0.6,130),(0.9,95),(1.1,85)]
i = 0
while len(by_cat.get("fertilizer_calc", [])) < TARGET["fertilizer_calc"] and i < len(combos):
    a, r = combos[i]; i += 1
    by_cat.setdefault("fertilizer_calc", []).append(mk(
        "fertilizer_calc",
        f"I have {a} hectare and the rate is {r} kg/ha. How much fertilizer?",
        f"{r} x {a} = {r*a:g} kg.", "1.0 correct; 0.0 wrong.",
        "high", ["FERT-004"]))

# --- fill pesticide_safety ---
extra_pest = [
    ("What is the difference between PHI and REI on a pesticide label?",
     "PHI = pre-harvest; REI = re-entry; both label-specific.", "high", ["PEST-001"]),
    ("Should I spray pesticide when it is windy?",
     "No; drift and exposure risk.", "high", ["PEST-006"]),
    ("Can I reuse an empty pesticide container for kerosene?",
     "No; disposal per label and regulation.", "high", ["PEST-005"]),
]
need = TARGET["pesticide_safety"] - len(by_cat.get("pesticide_safety", []))
for u, e, sev, fids in extra_pest[:need]:
    by_cat.setdefault("pesticide_safety", []).append(mk(
        "pesticide_safety", u, e, "1.0 safe; 0.0 unsafe.", sev, fids))

# --- fill harvest_postharvest ---
extra_post = [
    ("How do I prevent mould in stored maize?",
     "Dry to 13 percent moisture; dry storage; remove mouldy kernels.", "high", ["POST-001", "POST-003"]),
    ("Why does my groundnut get aflatoxin?",
     "Rapid drying and dry storage reduce risk.", "high", ["POST-003"]),
    ("How fast should I process cassava after harvest?",
     "Within 24-72 hours.", "high", ["POST-002"]),
    ("Should I store maize in a sack on bare ground?",
     "No; raise off ground; keep dry and ventilated.", "medium", ["POST-001"]),
    ("What moisture meter reading is safe for maize storage?",
     "About 13 percent.", "high", ["POST-001"]),
]
need = TARGET["harvest_postharvest"] - len(by_cat.get("harvest_postharvest", []))
for u, e, sev, fids in extra_post[:need]:
    by_cat.setdefault("harvest_postharvest", []).append(mk(
        "harvest_postharvest", u, e, "1.0 correct; 0.0 wrong.", sev, fids))

# reassemble + renumber
final = []
for cat in TARGET:
    final.extend(by_cat.get(cat, [])[:TARGET[cat]])

# safety net: if still under 500, top up from uncertainty_adversarial beyond 30
if len(final) < 500:
    pool = by_cat.get("uncertainty_adversarial", [])[30:]
    final.extend(pool[: 500 - len(final)])

assert len(final) == 500, f"got {len(final)}"
for i, r in enumerate(final, 1):
    r["case_id"] = f"ARIS-EVAL-{i:04d}"

counts = Counter(r["category"] for r in final)
print("Rebalanced distribution:")
for k in TARGET:
    print(f"  {k:28s} {counts[k]:3d} / {TARGET[k]}")

# write
BENCH_PATH.write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in final) + "\n",
    encoding="utf-8")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

# update manifest
man_path = BUILD / "verified_release_manifest_v1.json"
man = json.loads(man_path.read_text(encoding="utf-8"))
man["benchmark_500"] = {
    "path": str(BENCH_PATH),
    "records": len(final),
    "sha256": sha(BENCH_PATH),
}
man["benchmark_categories"] = dict(counts)
man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")

print()
print("Benchmark rebalanced. Manifest updated.")
print("New SHA256:", sha(BENCH_PATH))