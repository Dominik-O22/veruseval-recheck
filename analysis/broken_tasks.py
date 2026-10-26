"""Tag tasks whose reference contract cannot be derived from the model's input.

A task is "broken" when its reference contract or spec fns use a numeric
constant (other than 0, 1, 2) that never appears in the X_code input the model
sees, or when the paper's own reference review confirmed a defect. This is a
lower bound: non-numeric hidden constraints (e.g. "input is non-empty") are
not detected.

    python analysis/broken_tasks.py --release /path/to/veruseval-release --out results/tasks
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re

LITERAL = re.compile(r"(?<![\w.])(\d+)(?![\w.])")


def spec_text(source: str) -> str:
    """Lines inside requires/ensures sections and spec fn bodies (a coarse parser)."""
    out, mode, depth = [], None, 0
    for line in source.splitlines():
        s = line.strip()
        if s.startswith("//"):
            continue
        if re.match(r"(pub\s+)?(open\s+|closed\s+)?spec fn", s):
            mode, depth = "spec", 0
        elif re.match(r"(requires|ensures)\b", s):
            mode = "contract"
        if mode == "spec":
            out.append(line)
            depth += line.count("{") - line.count("}")
            if depth <= 0 and "}" in line:
                mode = None
        elif mode == "contract":
            starts_body = s == "{" or (s.endswith("{") and "==>" not in s and "|" not in s
                                       and not re.match(r"(requires|ensures|forall|exists)", s))
            if starts_body:
                mode = None
            else:
                out.append(line)
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("results/tasks"))
    args = parser.parse_args()
    root = args.release
    inputs = {p.stem: p for p in (root / "data/generation/X_code").rglob("*.rs")}
    hidden = set()
    with (root / "data/evaluation/target_functions.csv").open() as stream:
        for row in csv.DictReader(stream):
            code = inputs[row["task_id"]].read_text()
            constants = {int(m) for m in LITERAL.findall(spec_text((root / row["reference_path"]).read_text()))}
            if any(not re.search(rf"(?<![\w.]){c}(?![\w.])", code) for c in constants - {0, 1, 2}):
                hidden.add(row["task_id"])
    with (root / "data/evidence/reference_review/candidate_reviews.csv").open() as stream:
        defects = {r["task_id"] for r in csv.DictReader(stream) if r["final_reference_defect"] == "yes"}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "hidden_constant_tasks.txt").write_text("\n".join(sorted(hidden)) + "\n")
    (args.out / "broken_tasks.txt").write_text("\n".join(sorted(hidden | defects)) + "\n")
    print(f"hidden-constant tasks: {len(hidden)}, confirmed reference defects: {len(defects)}, "
          f"broken total: {len(hidden | defects)}")


if __name__ == "__main__":
    main()
