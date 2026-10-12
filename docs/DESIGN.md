# Design notes

## Why a fact ledger

Generating 500 agricultural answers is a coding task. Establishing that they are correct is a verification task. This repository separates the two.

Every training record references `fact_id` values. Every `fact_id` carries a source URL, source name, conditions, and status.

## Status values

| Status | Meaning | Trains? |
|---|---|---|
| `verified` | Sourced and consistent across authorities | Yes |
| `conditional` | Sourced but depends on region, crop stage, or soil test | Yes, with the condition stated |
| `time_sensitive` | Correct now, will drift | No |
| `uncertain` | Flagged for review | No |

## Why the benchmark is separate

NCAIR requires measurable improvement over base N-ATLaS on a benchmark of at least 500 examples. If any benchmark case leaks into training, the measurement is invalid. The benchmark is a separate file, verified by SHA256 in the release manifest.

## The FAW-vs-CMD distinction

The most common failure mode in the original ARIS dataset was confusing fall armyworm (an insect on maize) with cassava mosaic disease (a virus on cassava). Ledger entries `FAW-*`, `CMD-*`, and `CMP-001` encode the correct distinction.
