"""
Four-level contamination audit between training corpus and evaluation sets.

Levels:
  1. Exact match (after lowercasing)
  2. Normalized match (NFKC, punctuation-stripped, whitespace-collapsed)
  3. Substring containment, both directions
  4. Near-duplicate detection (token-set Jaccard >= 0.90)

Output: build/contamination_audit_v1.json
"""
import json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
BUILD = ROOT / "build"

TRAIN = PROC / "aris_natlas_train_v1.jsonl"
BENCH = PROC / "aris_benchmark_500_v1.jsonl"
FROZEN = ROOT / "data" / "eval" / "frozen" / "ARIS_V10_EVAL_FROZEN_V3.jsonl"

JACCARD_THRESHOLD = 0.90

def load_user_prompts(path):
    """Return list of user-role message strings from a JSONL file."""
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        for m in rec.get("messages", rec.get("input_messages", [])):
            if m.get("role") == "user":
                out.append(m["content"])
                break
    return out

def normalize(text):
    t = unicodedata.normalize("NFKC", text).lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def tokens(text):
    return set(normalize(text).split())

def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def audit(train_path, eval_path, label):
    train = load_user_prompts(train_path)
    evals = load_user_prompts(eval_path)
    if not train or not evals:
        return {"skipped": True, "reason": f"missing {train_path.name} or {eval_path.name}"}

    train_lc = [p.strip().lower() for p in train]
    eval_lc = [p.strip().lower() for p in evals]
    train_norm = set(normalize(p) for p in train)
    eval_norm = set(normalize(p) for p in evals)

    exact = sorted(set(eval_lc) & set(train_lc))
    norm_dupes = sorted(eval_norm & train_norm)

    sub_e_in_t = []
    for e in eval_norm:
        for t in train_norm:
            if e in t and e != t:
                sub_e_in_t.append((e, t))
                break
    sub_t_in_e = []
    for t in train_norm:
        for e in eval_norm:
            if t in e and t != e:
                sub_t_in_e.append((t, e))
                break

    near = []
    for e in evals:
        best = (0.0, "")
        for t in train:
            s = jaccard(e, t)
            if s > best[0]:
                best = (s, t)
        if best[0] >= JACCARD_THRESHOLD:
            near.append((e, best[1], round(best[0], 3)))

    verdict = "CLEAN" if not (exact or norm_dupes or sub_e_in_t or sub_t_in_e or near) else "REVIEW"

    return {
        "label": label,
        "eval_prompts": len(evals),
        "train_prompts": len(train),
        "level_1_exact": len(exact),
        "level_2_normalized": len(norm_dupes),
        "level_3_eval_in_train": len(sub_e_in_t),
        "level_3_train_in_eval": len(sub_t_in_e),
        "level_4_near_duplicate": len(near),
        "verdict": verdict,
        "samples": {
            "exact": exact[:5],
            "normalized": norm_dupes[:5],
            "eval_in_train": [{"eval": e, "train": t[:100]} for e, t in sub_e_in_t[:5]],
            "train_in_eval": [{"train": t, "eval": e[:100]} for t, e in sub_t_in_e[:5]],
            "near_dup": [{"eval": e[:100], "train": t[:100], "jaccard": s} for e, t, s in near[:5]],
        },
    }

print(f"{'=' * 72}")
print(f"CONTAMINATION AUDIT — 4 LEVELS")
print(f"{'=' * 72}")

results = {
    "benchmark_audit": audit(TRAIN, BENCH, "training vs 500-case benchmark"),
    "frozen_audit": audit(TRAIN, FROZEN, "training vs frozen NCAIR rubric"),
}

for key, r in results.items():
    print(f"\n{key} ({r.get('label', '?')}):")
    if r.get("skipped"):
        print(f"  SKIPPED: {r['reason']}")
        continue
    print(f"  eval prompts:      {r['eval_prompts']}")
    print(f"  train prompts:     {r['train_prompts']}")
    print(f"  L1 exact:          {r['level_1_exact']}")
    print(f"  L2 normalized:     {r['level_2_normalized']}")
    print(f"  L3 eval in train:  {r['level_3_eval_in_train']}")
    print(f"  L3 train in eval:  {r['level_3_train_in_eval']}")
    print(f"  L4 near-dup:       {r['level_4_near_duplicate']}")
    print(f"  VERDICT:           {r['verdict']}")

    if r["level_3_train_in_eval"]:
        print(f"\n  --- reverse substring flags ---")
        for s in r["samples"]["train_in_eval"]:
            print(f"  train: {s['train'][:80]}")
            print(f"  eval:  {s['eval'][:80]}\n")

BUILD.mkdir(exist_ok=True)
out = BUILD / "contamination_audit_v1.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved: {out}")