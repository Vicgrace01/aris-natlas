# Dataset Card — ARIS powered by N-ATLaS

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
