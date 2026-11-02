"""Part A: where attempts are lost before any contract comparison. No model calls, no Verus.

Sorts each failure before proving by a fixed rule on Verus's first error:

    Malformed output   the file cannot be parsed as code at all: unclosed or stray delimiters, stray tokens
    Verus-specific     the diagnostic's own words name something that exists only in Verus
    General Rust       any other type, name or syntax error
    No diagnostic      Verus stopped without one, such as an internal panic

The rule reads the diagnostic's message and labels, never the echoed source. A wide variant that also reads
the source is reported beside it, because many errors sit inside Verus-only code without saying so. The true
share lies between the two.

    python3 -I analysis/part_a.py --release REL --out DIR [--sample 60]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import random
import re

MALFORMED = re.compile(r"unclosed delimiter|unexpected closing delimiter|unknown start of token|mismatched closing delimiter"
                       r"|unterminated|this file contains", re.I)
VERUS = re.compile(r"\b(int|nat|Seq|Set|Map|Multiset|ghost|tracked|spec|proof|requires|ensures|invariant|decreases|forall|exists|choose"
                   r"|vstd|builtin|recommends|old|broadcast|verus|verifier|view|spec_\w+|mode)\b|`@|@`|==>|===|=~=", re.I)
FACTORS = ("workflow", "model", "shot", "task_id")


def first_error(metrics: dict) -> tuple[str, str]:
    """The first error's own words, and those words plus the rendered source. Both empty if there is none."""
    for key in ("parse_rate", "type_check_rate"):
        frontend = ((metrics.get(key) or {}).get("generated") or {}).get("frontend") or {}
        for line in (frontend.get("stderr") or "").splitlines():
            if not line.startswith("{"):
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("level") == "error" and "aborting due to" not in item.get("message", ""):
                own = [item.get("message", "")] + [s.get("label") or "" for s in item.get("spans") or []]
                own += [c.get("message", "") for c in item.get("children") or []]
                words = "\n".join(own)
                return words, f"{words}\n{item.get('rendered') or ''}"
    return "", ""


def classify(text: str) -> str:
    if not text:
        return "No diagnostic"
    if MALFORMED.search(text.split("\n", 1)[0]):
        return "Malformed output"
    return "Verus-specific" if VERUS.search(re.sub(r"-->[^\n]*", "", text)) else "General Rust"


def eta_squared(rows: list[dict], factor: str) -> float:
    """Share of the variance in verified that this factor explains on its own, adjusted for how many levels it has."""
    mean = sum(r["verified"] for r in rows) / len(rows)
    total = sum((r["verified"] - mean) ** 2 for r in rows)
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        groups[row[factor]].append(row["verified"])
    raw = sum(len(g) * (sum(g) / len(g) - mean) ** 2 for g in groups.values()) / total
    return 1 - (1 - raw) * (len(rows) - 1) / (len(rows) - len(groups))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample", type=int, default=60)
    args = parser.parse_args()
    root = args.release
    with (root / "data/evaluation/artifact_index.csv").open() as stream:
        index = {r["sample_id"]: r["result_path"] for r in csv.DictReader(stream)}
    with (root / "data/evaluation/rq1_artifact_labels.csv").open() as stream:
        labels = [r for r in csv.DictReader(stream) if r["analysis_eligible"] == "True"]
    rows, failures = [], []
    for label in labels:
        verified = label["verification_stage"] == "accepted"
        rows.append({**{f: label[f] for f in FACTORS}, "verified": int(verified)})
        if label["verification_stage"] in ("frontend_failed", "parse_failed"):
            metrics = json.loads((root / index[label["sample_id"]]).read_text())["metrics"]
            words, full = first_error(metrics)
            failures.append({"sample": label["sample_id"], "stage": label["verification_stage"], "workflow": label["workflow"],
                             "model": label["model"], "shot": label["shot"], "text": full[:900], "class": classify(words), "wide": classify(full)})
    configs: dict[tuple, list[int]] = defaultdict(list)
    for row in rows:
        configs[(row["workflow"], row["model"], row["shot"])].append(row["verified"])
    pairs = []
    for (workflow, model, shot), values in configs.items():
        if shot == "few-shot" and (workflow, model, "zero-shot") in configs:
            zero = configs[(workflow, model, "zero-shot")]
            pairs.append({"workflow": workflow, "model": model, "few": sum(values) / len(values), "zero": sum(zero) / len(zero)})
    report = {
        "attempts": len(rows), "verified": sum(r["verified"] for r in rows), "stages": dict(Counter(l["verification_stage"] for l in labels)),
        "failure_classes": dict(Counter(f["class"] for f in failures)),
        "failure_classes_wide": dict(Counter(f["wide"] for f in failures)),
        "first_error_int_index": sum("expected `int`, found `usize`" in f["text"] for f in failures),
        "first_error_by_message": Counter(re.sub(r"`[^`]*`", "`_`", f["text"].split("\n", 1)[0])[:70] for f in failures).most_common(12),
        "class_by_model": {m: dict(Counter(f["class"] for f in failures if f["model"] == m)) for m in sorted({f["model"] for f in failures})},
        "class_by_shot": {s: dict(Counter(f["class"] for f in failures if f["shot"] == s)) for s in ("few-shot", "zero-shot")},
        "variance_explained": {f: round(eta_squared(rows, f), 4) for f in FACTORS},
        "config_range": {"low": min(sum(v) / len(v) for v in configs.values()), "high": max(sum(v) / len(v) for v in configs.values())},
        "prompting_pairs": sorted(pairs, key=lambda p: p["few"] - p["zero"]),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "part_a.json").write_text(json.dumps(report, indent=2) + "\n")
    rng = random.Random(20261102)
    sample = rng.sample(failures, args.sample)
    (args.out / "hand_check.jsonl").write_text("".join(json.dumps(f) + "\n" for f in sample))
    print(json.dumps({k: report[k] for k in ("failure_classes", "class_by_shot", "class_by_model", "variance_explained", "config_range")}, indent=1))
    print(json.dumps(report["prompting_pairs"]))


if __name__ == "__main__":
    main()
