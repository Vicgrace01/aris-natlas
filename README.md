\# ARIS powered by N-ATLaS



Source-backed offline agricultural advisory for Nigerian smallholder farmers,

built on NCAIR's N-ATLaS (Llama 3 8B instruction-tuned).



\## What this repository contains



| Artifact | Path | Purpose |

|---|---|---|

| \*\*Technical report\*\* | \[`REPORT.md`](REPORT.md) | The narrative artifact — read this first |

| Fact ledger | `data/processed/aris\_fact\_ledger\_v1.jsonl` | Source-backed agricultural facts (IITA, FAO, NRCRI, NAERLS) |

| Corrected training | `data/processed/aris\_corrected\_training\_v1.jsonl` | Targeted fixes for known failure modes |

| Expanded training | `data/processed/aris\_expanded\_training\_v1.jsonl` | Provenance-carrying training records |

| 500-case benchmark | `data/processed/aris\_benchmark\_500\_v1.jsonl` | Independent evaluation set, never trained on |

| Red-team battery | `data/processed/aris\_redteam\_battery\_v1.jsonl` | Adversarial safety probes |

| Release manifest | `build/verified\_release\_manifest\_v1.json` | SHA256 hashes of every artifact |

| Frozen NCAIR rubric | `data/eval/frozen/` | Byte-for-byte preserved |



\## Design principles



1\. \*\*No unsupported claims.\*\* Every agricultural assertion in training data

&#x20;  traces to a `fact\_id` in the ledger. Every ledger entry carries a source URL

&#x20;  and a status.

2\. \*\*Evaluation is separate from training.\*\* The 500-case benchmark is never

&#x20;  mixed into the training corpus. This is audited by

&#x20;  `scripts/16\_contamination\_audit.py` and enforced by CI.

3\. \*\*Provenance is machine-readable.\*\* Each record's `provenance.fact\_ids`

&#x20;  field names the ledger entries that justify it.

4\. \*\*The frozen rubric is immutable.\*\* `data/eval/frozen/ARIS\_V10\_EVAL\_FROZEN\_V3.jsonl`

&#x20;  has not been modified since it was received from NCAIR.

5\. \*\*Refusal is trained, not prompted.\*\* The model is fine-tuned to refuse

&#x20;  unsafe dosages, invented product names, and diagnoses from text alone.



\## Reproducing the build



See \[`docs/REPRODUCE.md`](docs/REPRODUCE.md). Short version:



```powershell

python scripts\\06\_build\_verified\_dataset.py

python scripts\\07\_rebalance\_benchmark.py

python scripts\\16\_contamination\_audit.py

python scripts\\17\_gate\_audit.py

python tests\\test\_artifacts.py



Verification

tests/test\_artifacts.py runs on every push to main and fails if any

manifest hash does not match the corresponding file. See

.github/workflows/verify.yml.



Sources

IITA, FAO, NRCRI, NAERLS. Full registry at

docs/SOURCE\_REGISTRY.md.



License

See LICENSE.

