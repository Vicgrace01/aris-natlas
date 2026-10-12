# Provenance

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
