"""
Create the multilingual scaffold. Records are marked enabled_for_training=false
until a native reviewer approves them. No translations are generated here.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ML = ROOT / "data" / "generated" / "multilingual"
ML.mkdir(parents=True, exist_ok=True)

# Each entry: source English prompt to be answered, plus the fact_ids
# any correct answer must respect. Native reviewers fill in the translation.
SEEDS = [
    ("What is the difference between fall armyworm and cassava mosaic disease?",
     ["FAW-001", "CMD-001", "CMP-001"]),
    ("How do I calculate fertilizer for my field?",
     ["FERT-003", "FERT-004"]),
    ("What is the pre-harvest interval for a pesticide?",
     ["PEST-004"]),
    ("How dry should maize be before storage?",
     ["POST-001"]),
    ("My cow is sick. What should I do?",
     ["LIVE-001", "VET-001"]),
    ("How do I identify cassava mosaic disease?",
     ["CMD-001", "CMD-002"]),
    ("What spacing should I use for maize?",
     ["SPC-001"]),
    ("Can I reuse a pesticide container for water?",
     ["PEST-005"]),
    ("How do I reduce aflatoxin in groundnut?",
     ["GRND-002", "POST-003"]),
    ("My poultry are dying suddenly. What should I do?",
     ["POUL-001", "VET-003"]),
]

LANGUAGES = {"ha": "Hausa", "ig": "Igbo", "yo": "Yoruba"}

records = []
i = 0
for lang_code, lang_name in LANGUAGES.items():
    for src, fact_ids in SEEDS:
        i += 1
        records.append({
            "record_id": f"ML-{lang_code.upper()}-{i:04d}",
            "language": lang_code,
            "language_name": lang_name,
            "source_english": src,
            "required_fact_ids": fact_ids,
            "translation_draft": None,
            "translation_reviewed": False,
            "reviewer_name": None,
            "reviewed_at": None,
            "enabled_for_training": False,
            "notes": "Fill translation_draft, set translation_reviewed=true and enabled_for_training=true only after native speaker review.",
        })

out = ML / "multilingual_seed_v1.jsonl"
with out.open("w", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Wrote {len(records)} seed records to {out}")
print(f"All disabled for training (enabled_for_training=false).")
print(f"Languages: {', '.join(LANGUAGES.values())}")
print()
print("Next: a native speaker fills translation_draft for each record,")
print("verifies it against required_fact_ids, then sets enabled_for_training=true.")