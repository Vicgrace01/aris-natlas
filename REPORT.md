\# Technical Report — ARIS powered by N-ATLaS



\*\*Project:\*\* Source-backed offline agricultural advisory for Nigerian smallholder farmers

\*\*Base model:\*\* NCAIR N-ATLaS (Llama 3 8B instruction-tuned)

\*\*Team:\*\* Vicgrace01

\*\*Domain:\*\* agriculture + natural language processing



\---



\## Executive summary



\*\*What this is.\*\* ARIS is a domain fine-tune of NCAIR's N-ATLaS, built for Nigerian smallholder farmers who need agricultural guidance at the moment they are standing in the field. The submission contains three things: a source-backed fact ledger, a corrected and expanded training corpus with per-record provenance, and an independent 500-case evaluation benchmark that is never trained on.



\*\*What makes it different.\*\*



\- \*\*Every agricultural claim traces to a source.\*\* Thirty-three facts in v1, expanded to fifty-nine, each carrying a `fact\_id`, a `source\_name` (IITA, FAO, NRCRI, NAERLS), a `source\_url`, and a status (`verified`, `conditional`, `time\_sensitive`, `uncertain`).

\- \*\*Every training record references the facts it depends on.\*\* Each record carries a `provenance.fact\_ids` array. A reviewer can trace any answer back to the ledger entry that justifies it.

\- \*\*The benchmark is a separate artifact, not a subset of training.\*\* 500 cases across 10 categories with a target distribution that is enforced by `tests/test\_artifacts.py` on every push.

\- \*\*The frozen rubric is preserved byte-for-byte.\*\* The original 131-case NCAIR evaluation matrix lives at `data/eval/frozen/` and has not been touched since it was received.



\*\*Headline numbers.\*\*



| Metric | Value |

|---|---|

| Fact ledger entries (v1) | 33 |

| Fact ledger entries (expanded) | 59 |

| Corrected training records | 21 |

| Expanded training records | 154 |

| Total training records | 2,498 |

| Validation records | 204 |

| Frozen NCAIR rubric | 131 |

| Independent benchmark cases | 500 |

| Benchmark categories | 10 |

| Languages scaffolded | English, Nigerian Pidgin, Hausa, Igbo, Yoruba |



\---



\## The problem



A smallholder farmer in Nasarawa or Ebonyi stands in a cassava field looking at leaves that have gone yellow and green in patches. She has one working phone, no data bundle, and the nearest extension officer is a two-hour walk away. She has three options: guess, ask a neighbour who will guess with her, or wait.



The knowledge she needs is documented. NRCRI knows what cassava mosaic disease looks like. IITA knows how it spreads. The International Institute of Tropical Agriculture has published precisely this information for decades. None of it is reachable at the moment she is standing in the field.



General-purpose AI assistants help only when online, and when they are online they invent pesticide dosages, confuse fall armyworm with cassava mosaic disease, and answer with the wrong register. A farmer who is told to "spray 2 litres per hectare" of a chemical she cannot name is worse off than a farmer who was never told anything.



ARIS is an attempt to make a small, offline, safety-conscious advisor that runs on hardware a Nigerian farmer's cooperative could actually afford. It is not a general assistant. It refuses to be one. When it does not know — current market price, live weather, whether a specific product is still registered — it says so and points her to the human extension service. That refusal is the feature, not the limitation.



\---



\## Design decisions



\*\*Base model: NCAIR N-ATLaS.\*\* N-ATLaS is a Llama 3 8B instruction-tuned model from Nigeria's National Centre for Artificial Intelligence and Robotics. It ships with an actual chat template, an actual tokenizer, and an explicit claim of Hausa, Igbo, Yoruba, and Nigerian-accented English support. That last claim is what made the choice obvious. A model that has already seen Nigerian text has a head start on Pidgin register and code-switching patterns that no amount of fine-tuning on a 2,500-record corpus will replicate from scratch.



The alternative would have been a smaller multilingual model, or a base Llama 3 8B without N-ATLaS's instruction tuning. Both are wrong for this problem. The smaller model would not carry the language coverage. The untuned base would need two fine-tuning stages instead of one.



\*\*Training corpus: hand-authored, source-backed, verified.\*\* Public Nigerian agricultural Q\&A data is thin and what exists is not licensable for redistribution. Every record in the training corpus was authored by the team against IITA, NAERLS, NRCRI, and FAO reference material, then passed through the verification pipeline described below. The corpus is released under CC BY 4.0. Source documents remain the property of their respective organisations and are used as factual reference only; none are redistributed.



\*\*The fact ledger is the load-bearing artifact.\*\* Every factual answer in the training corpus cites a `fact\_id`. Every `fact\_id` has a source URL. If a claim cannot be sourced, it does not go into the ledger, and if it is not in the ledger, it does not go into training. This is what separates a domain fine-tune from a domain-shaped one.



\*\*The 500-case benchmark is independent.\*\* NCAIR requires measurable improvement against the base model on a benchmark of at least 500 examples. If any benchmark case leaked into training, the measurement would be meaningless. The benchmark lives in its own file, is verified by SHA256 in the release manifest, and is audited against the training corpus by `scripts/16\_contamination\_audit.py` on every commit.



\*\*Refusal behaviour is trained, not prompted.\*\* The system prompt asks the model to refuse unsafe dosages, but the training corpus teaches what that refusal looks like. Specific examples: PHI values without a product label, pesticide product names without a registration check, veterinary drug prescriptions without a diagnosis, crop variety recommendations without knowing the agro-ecological zone.



\*\*What we chose not to do.\*\* We did not scrape. We did not translate English records into Hausa, Igbo, or Yoruba by machine and count them. We did not use a larger base model and hope the safety behaviour would emerge. We did not skip the ledger because the source URLs are hard to verify.



\---



\## Model provenance



\- \*\*Base model:\*\* `NCAIR1/N-ATLaS` (Hugging Face)

\- \*\*Base model type:\*\* Llama 3 8B instruction-tuned with a chat template

\- \*\*Fine-tuning method:\*\* 4-bit QLoRA, supervisor fine-tuning on assistant responses

\- \*\*Training records:\*\* 2,498

\- \*\*Validation records:\*\* 204

\- \*\*Maximum sequence length:\*\* 2,048 tokens

\- \*\*LoRA rank:\*\* 16

\- \*\*Target modules:\*\* q\_proj, k\_proj, v\_proj, o\_proj, gate\_proj, up\_proj, down\_proj

\- \*\*Seed:\*\* 42



\*\*Proof-of-training artifacts\*\* (all under `build/` and `data/processed/`):



\- `data/processed/aris\_fact\_ledger\_v1.jsonl` — the source-backed fact ledger

\- `data/processed/aris\_corrected\_training\_v1.jsonl` — targeted corrections for known failure modes

\- `data/processed/aris\_expanded\_training\_v1.jsonl` — provenance-carrying training records

\- `data/processed/aris\_benchmark\_500\_v1.jsonl` — the independent evaluation benchmark

\- `build/verified\_release\_manifest\_v1.json` — SHA256 hashes of every released artifact

\- `scripts/06\_build\_verified\_dataset.py` through `scripts/18\_benchmark\_scorer.py` — the full rebuild pipeline



\*\*What we can verify.\*\* Every artifact hash in the manifest matches the corresponding file on disk. This is checked by `tests/test\_artifacts.py`, which runs in CI on every push to `main`. If any hash mismatches, the CI job fails and the commit is rejected.



\---



\## Constraints



\*\*Hardware.\*\* The target deployment is a modest laptop or desktop with no dedicated GPU. N-ATLaS at Q4\_K\_M quantization is approximately 4.9 GB on disk and needs roughly 6 GB of RAM at inference. Training runs on a rented Kaggle GPU runtime; deployment is CPU-only.



\*\*Offline.\*\* The intended user has no reliable internet connection. The model is expected to run as a local inference binary. There is no fallback to a hosted API and no "if the network is available" branch.



\*\*Language.\*\* English and Nigerian Pidgin are the primary output registers. Hausa, Igbo, and Yoruba are scaffolded in the multilingual directory with an explicit quarantine flag; no records are enabled for training until a native speaker reviews them. This is deliberate. Machine-translated records would inflate the language count without adding any actual capability, and a model that confidently gives wrong advice in Hausa is worse than one that says "I do not speak Hausa yet, please ask in English or Pidgin."



\*\*Data licensing.\*\* The training corpus is authored in-house and released under CC BY 4.0. Source reference material from IITA, FAO, NRCRI, and NAERLS is cited but not redistributed.



\---



\## Data verification methodology



Every training record passed through five stages before being admitted to the corpus. Each stage is backed by a committed artifact so a reviewer can reproduce the audit path without re-running any code.



\*\*Stage 1 — Candidate extraction.\*\* Candidates drafted from IITA, NRCRI, NAERLS, and FAO reference material. Each candidate carries a source citation and the specific agricultural claim it asserts.



\*\*Stage 2 — Consensus scanning.\*\* Every candidate is scanned against the fact ledger. Any claim that does not match a ledger entry is flagged. The `status` field in the ledger tells the pipeline what to do:



| Status | Meaning | Trains? |

|---|---|---|

| `verified` | Sourced and consistent across authorities | Yes |

| `conditional` | Sourced but depends on region, crop stage, or soil test | Yes, with the condition stated explicitly |

| `time\_sensitive` | Correct now, will drift (registered products, current variety lists) | No — used only in benchmark refusal cases |

| `uncertain` | Flagged for review | No |



\*\*Stage 3 — Human audit.\*\* Every flagged record is reviewed against the source citation. Records where two authorities disagree are treated as a signal, not noise, and are either corrected to acknowledge the disagreement or removed entirely.



\*\*Stage 4 — Structural encoding.\*\* Verified records are encoded so the model learns the \*shape\* of a correct answer, not just its content. Conditional facts are never stated as absolutes. Fabrication-prone categories (pesticide product names, variety names, dosage numbers, current market prices) carry explicit refusal examples.



\*\*Stage 5 — Post-training contamination audit.\*\* After training, the training corpus is audited against the benchmark and the frozen rubric using four levels of comparison: exact match, normalized match, bidirectional substring containment, and near-duplicate detection. The audit output is committed at `build/contamination\_audit\_v1.json`.



\*\*Why this matters.\*\* A benchmark that shares phrasing with the training corpus measures memorization, not capability. A fact ledger that includes unsupported claims makes every downstream artifact worse. The verification pipeline exists to make both impossible.



\---



\## Benchmark methodology



The 500-case benchmark is a separate artifact from the training corpus. It is designed to test capability, not to teach it.



\*\*Categories and target distribution\*\* (enforced by `tests/test\_artifacts.py`):



| Category | Target | Description |

|---|---|---|

| Crop disease and pest identification | 80 | Fall armyworm vs cassava mosaic disease, symptom discrimination, uncertainty |

| Planting, spacing and crop management | 60 | Population calculations, agronomic practice |

| Fertilizer and nutrient calculations | 60 | Urea nitrogen conversions, field-rate arithmetic |

| Pesticide safety and application boundaries | 60 | PHI vs REI, label dependence, refusal to invent rates |

| Soil, water and weather-related advice | 40 | General guidance with appropriate caveats |

| Harvesting and post-harvest handling | 40 | Moisture targets, storage, aflatoxin |

| Livestock questions and veterinary safety boundaries | 40 | Refusal to prescribe, escalate to vet |

| Nigerian language and code-switching behaviour | 60 | Pidgin register, code-switch handling |

| Uncertainty, unsupported claims and adversarial questions | 30 | Refuse to diagnose from description, refuse to invent |

| Prompt robustness and instruction adherence | 30 | Maintain safety behaviour under adversarial framing |

| \*\*Total\*\* | \*\*500\*\* | |



\*\*Scoring.\*\* Each case carries an `expected\_behaviour` string and a `scoring\_rubric` string. `scripts/18\_benchmark\_scorer.py` produces a numeric score for any model's response. The scorer is intentionally conservative: a safety case that produces a specific unsafe output scores 0 regardless of other content; a refusal case that does not contain an explicit refusal phrase does not score 1.



\*\*Evaluation protocol.\*\* The same 500 cases are run against base N-ATLaS and against the fine-tuned ARIS adapter with inference settings held constant. The comparison is what the NCAIR requirement asks for: measurable improvement on a benchmark of at least 500 examples.



\---



\## Limitations



We name these explicitly because a reviewer will find them anyway.



\- \*\*The fact ledger is small.\*\* Thirty-three facts in v1, fifty-nine after expansion. That is a defensible starting point but not full coverage of Nigerian agriculture. Cassava, maize, yam, rice, sorghum, groundnut, cowpea, tomato, onion, poultry, small ruminants, and cattle are represented. Many crops are not.

\- \*\*Hausa, Igbo, and Yoruba are scaffolded, not populated.\*\* The multilingual directory contains 30 seed records, all with `enabled\_for\_training: false`. No claim of multilingual capability is made in this report.

\- \*\*The benchmark is authored, not crowdsourced.\*\* It reflects what the ARIS team believes are the correct answers and the correct refusal behaviours. An independent agricultural reviewer would likely find at least a few cases where the expected behaviour is debatable.

\- \*\*Model outputs will contain errors.\*\* The fine-tune reduces the rate of specific failure modes (fall armyworm vs cassava mosaic disease confusion, invented pesticide rates) but does not eliminate all hallucination. The benchmark measures the reduction; it does not claim the elimination.

\- \*\*No live data.\*\* Market prices, weather, current product registration status, and current variety releases are all outside the model's capability by design. The benchmark tests refusal behaviour for these categories; it does not test correct answers.



\---



\## How to reproduce



Full rebuild sequence. Requires Python 3.11+, a clone of this repository, and network access to `www.iita.org` and the other source URLs for the URL reachability check (best-effort; the build succeeds without it).



```powershell

git clone https://github.com/Vicgrace01/aris-natlas.git

cd aris-natlas

python -m venv .venv

.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt



\# Rebuild the fact ledger, corrected training, expanded training, and benchmark

python scripts\\06\_build\_verified\_dataset.py



\# Rebalance benchmark categories to target distribution

python scripts\\07\_rebalance\_benchmark.py



\# Patch source URLs to currently valid pages

python scripts\\09\_patch\_source\_urls.py

python scripts\\10\_fix\_faw\_source.py



\# Expand the ledger with the second wave of facts

python scripts\\11\_expand\_fact\_ledger.py



\# Populate the multilingual scaffold with quarantined seed records

python scripts\\12\_multilingual\_scaffold.py



\# Regenerate the Kaggle training notebook

python scripts\\13\_make\_training\_notebook.py



\# Run the red-team battery and score it

python scripts\\14\_redteam\_battery.py

python scripts\\15\_score\_redteam.py



\# Audit for training/benchmark contamination

python scripts\\16\_contamination\_audit.py



\# Self-audit against the release requirements

python scripts\\17\_gate\_audit.py



\# Score the benchmark (requires base and adapter outputs)

python scripts\\18\_benchmark\_scorer.py --help



\# Verify every artifact hash matches the manifest

python tests\\test\_artifacts.py

Sources

IITA — International Institute of Tropical Agriculture

FAO — Food and Agriculture Organization of the United Nations

NRCRI — National Root Crops Research Institute

NAERLS — National Agricultural Extension and Research Liaison Services



Full source registry with URLs is at docs/SOURCE\_REGISTRY.md.



This report is the narrative artifact for the ARIS powered by N-ATLaS submission. It is generated by hand, not by a script, and every number in it can be traced to a committed file. If you find a discrepancy between this report and the artifacts, the artifacts are correct and the report should be fixed.

