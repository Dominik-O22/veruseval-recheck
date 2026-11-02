"""Tables for RQ1, RQ3 and RQ4 from the verdict table and the release's labels. No model calls, no Verus.

A clause lands in one class, by its guarded and unconditional verdicts:

    Difference     refuted in the guarded form, or on L1, by a plain witness
    Premise only   proved guarded, refuted unconditionally by a plain witness
    Solver limit   proved in both forms
    Guarded only   proved guarded, undecided unconditionally
    Certified false, unlocated   refuted unconditionally by a plain witness, guarded undecided
    Computed       the only refutation uses a computed value, which is never a real difference
    Unrepresentable  the only refutation needs a value no program can build, such as a Vec of usize::MAX
    Undecided      nothing established

An artifact is, in order: Trivial if the paper's check holds, Difference if any clause is, Sound if every
rejected clause is Solver limit or Premise only, otherwise Undecided. Artifacts the release did not reject on
L1 or L2 are Clean. One the release rejected with no clause row stays Undecided. L3 and L4 are out of scope,
so none of these means equivalent or correct.

    python3 -I analysis/census_report.py --verdicts verdicts.jsonl --labels rq1_artifact_labels.csv --out DIR \\
        [--rq4-verdicts verdicts.jsonl --rq4-stages stages.jsonl --rq4-tasks results/tasks/rq4_tasks.txt] [--rq2 rq2.jsonl]
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import random

CLASSES = ("Difference", "Premise only", "Solver limit", "Guarded only", "Certified false, unlocated", "Computed",
           "Unrepresentable", "Undecided")
ARTIFACTS = ("Trivial", "Clean", "Sound", "Difference", "Undecided")


def plain_refuted(entry: dict) -> bool:
    return entry["verdict"] == "refuted" and not entry.get("computed") and entry.get("realized") is not False


def weak_refutation(*entries: dict) -> str:
    """The class of a refutation that is not a plain, runnable one."""
    return "Computed" if any(e.get("computed") for e in entries) else "Unrepresentable"


def clause_class(row: dict) -> str:
    uncond, guarded = row["uncond"], row["guarded"]
    if plain_refuted(guarded) or (row["direction"] == "L1" and plain_refuted(uncond)):
        return "Difference"
    if guarded["verdict"] == "proved":
        if uncond["verdict"] == "proved":
            return "Solver limit"
        if plain_refuted(uncond):
            return "Premise only"
        return weak_refutation(uncond) if uncond["verdict"] == "refuted" else "Guarded only"
    if plain_refuted(uncond):
        return "Certified false, unlocated"
    return weak_refutation(uncond, guarded) if "refuted" in (uncond["verdict"], guarded["verdict"]) else "Undecided"


def artifact_class(classes: list[str], trivial: bool) -> str:
    if trivial:
        return "Trivial"
    if not classes:
        return "Clean"
    if "Difference" in classes:
        return "Difference"
    return "Sound" if all(c in ("Solver limit", "Premise only") for c in classes) else "Undecided"


def config(sample: str) -> str:
    return "|".join(sample.split("|")[:3])


def rq1(table: list[dict]) -> dict:
    grid = Counter((r["guarded"]["verdict"], r["uncond"]["verdict"]) for r in table)
    impossible = grid[("refuted", "proved")]
    return {"clauses": len(table), "classes": {c: sum(clause_class(r) == c for r in table) for c in CLASSES},
            "by_direction": {d: dict(Counter(clause_class(r) for r in table if r["direction"] == d)) for d in ("L1", "L2")},
            "grid": {f"{g} / {u}": n for (g, u), n in sorted(grid.items())}, "impossible_cell": impossible,
            "by_tier": dict(Counter((r["uncond"].get("tier") or "none").split(":")[0] for r in table))}


def unsettled(row: dict, by_sample: dict) -> bool:
    """The release did not pass this artifact on L1 and L2, and no clause row explains why."""
    return row.get("formal_reliability_state") in ("other", "unfavorable") and row["sample_id"] not in by_sample


def artifacts(table: list[dict], labels: list[dict]) -> dict[str, str]:
    by_sample: dict[str, list[str]] = defaultdict(list)
    for row in table:
        by_sample[row["sample"]].append(clause_class(row))
    return {row["sample_id"]: "Undecided" if unsettled(row, by_sample)
            else artifact_class(by_sample.get(row["sample_id"], []), row["triviality_state"] == "unfavorable")
            for row in labels}


def rq3(classes: dict[str, str], labels: list[dict], table: list[dict]) -> dict:
    rejected = {r["sample"] for r in table}
    passing = [r["sample_id"] for r in labels if r["io_state"] == "favorable"]
    among = [s for s in passing if s in rejected]
    return {"io_passing": len(passing), "io_passing_with_rejection": len(among),
            "outcome": dict(Counter(classes[s] for s in among)),
            "by_config": {c: dict(Counter(classes[r["sample_id"]] for r in labels if config(r["sample_id"]) == c))
                          for c in sorted({config(r["sample_id"]) for r in labels})}}


def concordance(rows: list[dict], seed: int = 20261102) -> dict:
    """Prompting pairs: same workflow and model, few-shot against zero-shot.

    rows: one per generated artifact, with workflow, model, shot, accepted, original and certified, the last
    two true when it passes that metric. Metrics are taken on accepted artifacts only. A pair is concordant
    when the setting with higher acceptance also scores higher. The negative control shuffles certified
    results among accepted artifacts, which shows how much relabeling alone moves the count.
    """
    def rate(group: list[dict], key: str) -> float:
        kept = [r for r in group if r["accepted"]]
        return sum(r[key] for r in kept) / len(kept) if kept else 0.0

    def count(table: list[dict], key: str) -> tuple[int, int]:
        pairs: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for row in table:
            pairs[(row["workflow"], row["model"])][row["shot"]].append(row)
        total = agree = 0
        for shots in pairs.values():
            few, zero = shots.get("few-shot", []), shots.get("zero-shot", [])
            if not any(r["accepted"] for r in few) or not any(r["accepted"] for r in zero):
                continue
            gap = sum(r["accepted"] for r in few) / len(few) - sum(r["accepted"] for r in zero) / len(zero)
            if gap == 0:
                continue
            total += 1
            agree += (rate(few, key) - rate(zero, key)) * gap > 0
        return agree, total

    rng = random.Random(seed)
    accepted = [r for r in rows if r["accepted"]]
    shuffled_labels = [r["certified"] for r in accepted]
    rng.shuffle(shuffled_labels)
    control = [dict(r) for r in rows]
    labels = iter(shuffled_labels)
    for row in control:
        if row["accepted"]:
            row["certified"] = next(labels)
    return {"original": count(rows, "original"), "certified": count(rows, "certified"), "relabel_control": count(control, "certified")}


def paired_bootstrap(left: list[int], right: list[int], rounds: int = 2000, seed: int = 20261102) -> tuple[float, float]:
    """95% interval for the mean paired difference, resampling tasks."""
    rng = random.Random(seed)
    pairs = list(zip(left, right))
    means = sorted(sum(a - b for a, b in rng.choices(pairs, k=len(pairs))) / len(pairs) for _ in range(rounds))
    return means[int(rounds * 0.025)], means[int(rounds * 0.975) - 1]


def rq4(attempts: dict[str, dict[str, str]]) -> dict:
    """attempts: model -> task -> Not verified, or an artifact class. Every model has every task."""
    tasks = sorted(next(iter(attempts.values())))
    sound = ("Clean", "Sound")
    out: dict = {}
    for model, outcome in attempts.items():
        n = len(tasks)
        count = Counter(outcome[t] for t in tasks)
        low = sum(count[c] for c in sound)
        out[model] = {"tasks": n, "verified": n - count["Not verified"], "sound_low": low,
                      "sound_high": low + count["Undecided"], "difference": count["Difference"],
                      "undecided": count["Undecided"], "trivial": count["Trivial"]}
    haiku = attempts["haiku-5-5"]
    for model, outcome in attempts.items():
        if model != "haiku-5-5":
            left = [int(haiku[t] in sound) for t in tasks]
            right = [int(outcome[t] in sound) for t in tasks]
            out[model]["haiku_minus_model_sound"] = paired_bootstrap(left, right)
    return out


def rq4_attempts(table: list[dict], labels: list[dict], haiku_table: list[dict], stages: list[dict],
                 tasks: list[str]) -> dict[str, dict[str, str]]:
    """Outcome per model and task on StarVerus few-shot. Triviality is not applied, because Haiku has no release label."""
    by_sample: dict[str, list[str]] = defaultdict(list)
    for row in [*table, *haiku_table]:
        by_sample[row["sample"]].append(clause_class(row))
    attempts: dict[str, dict[str, str]] = {"haiku-5-5": {t: "Not verified" for t in tasks}}
    for row in stages:
        if row["accepted"]:
            attempts["haiku-5-5"][row["task"]] = artifact_class(by_sample.get(row["label"], []), False)
    for row in labels:
        if row["workflow"] == "StarVerus" and row["shot"] == "few-shot" and row["task_id"] in tasks:
            model = attempts.setdefault(row["model"], {t: "Not verified" for t in tasks})
            model[row["task_id"]] = "Undecided" if unsettled(row, by_sample) else artifact_class(by_sample.get(row["sample_id"], []), False)
    return attempts


def rq2(rows: list[dict]) -> dict:
    """Tasks where a sound, same-code contract shows the reference rejects an input the code handles."""
    counted = {r["task"] for r in rows if r["refuted"] and r["realized"]}
    return {"tasks_searched": len({r["task"] for r in rows}), "tasks_counted": len(counted), "tasks": sorted(counted)}


def rq5(rows: list[dict], hidden: set[str], tasks: list[str], hidden_share: float) -> dict:
    """Paired by task across Haiku's four arms: few or zero examples, with or without task text.

    rows carry arm (few-plain, few-text, zero-plain or zero-text), task, accepted and L1 to L4.
    A task that does not verify, or produced no program, counts as not passing, so failure is not hidden.
    """
    arms: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        arms[row["arm"]][row["task"]] = row

    def passed(arm: str, task: str, key: str) -> int:
        row = arms[arm].get(task, {})
        return int(bool(row.get("accepted")) if key == "verified" else row.get(key) == "valid")

    def compare(left: str, right: str, group: list[str]) -> dict:
        out: dict = {"tasks": len(group)}
        for key in ("verified", "L1", "L2", "L3", "L4"):
            a, b = [passed(left, t, key) for t in group], [passed(right, t, key) for t in group]
            out[key] = {left: sum(a), right: sum(b), "difference": paired_bootstrap(a, b) if group else None}
        return out

    def mean_difference(result: dict, left: str, right: str, key: str) -> float:
        return (result[key][left] - result[key][right]) / result["tasks"] if result["tasks"] else 0.0

    report = {}
    for name, (left, right) in {"text_with_examples": ("few-text", "few-plain"), "text_without_examples": ("zero-text", "zero-plain"),
                                "examples_without_text": ("few-plain", "zero-plain")}.items():
        report[name] = {"all": compare(left, right, tasks), "hidden_constant": compare(left, right, [t for t in tasks if t in hidden]),
                        "other": compare(left, right, [t for t in tasks if t not in hidden]),
                        "vericoding": compare(left, right, [t for t in tasks if t.startswith("VeriCoding")]),
                        "other_sources": compare(left, right, [t for t in tasks if not t.startswith("VeriCoding")])}
        report[name]["pool_weighted"] = {key: round(hidden_share * mean_difference(report[name]["hidden_constant"], left, right, key)
                                                    + (1 - hidden_share) * mean_difference(report[name]["other"], left, right, key), 4)
                                         for key in ("verified", "L1", "L2", "L3", "L4")}
    return report


def rows_of(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verdicts", type=Path, nargs="+", required=True, help="dev and census tables together")
    parser.add_argument("--partial", action="store_true", help="dry runs only: accept a table that misses rejected artifacts")
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rq4-verdicts", type=Path)
    parser.add_argument("--rq4-stages", type=Path)
    parser.add_argument("--rq4-tasks", type=Path)
    parser.add_argument("--rq2", type=Path)
    parser.add_argument("--rq5", type=Path, help="labels with arm in the label field, as few-plain|task and so on")
    parser.add_argument("--hidden", type=Path, help="hidden-constant task list, for RQ5")
    parser.add_argument("--rq5-tasks", type=Path, help="the sampled tasks, for RQ5")
    parser.add_argument("--rq5-pool", type=Path, help="the pool they were drawn from, for weighting")
    parser.add_argument("--drop", type=Path, nargs="*", help="task lists to leave out, one sensitivity check each")
    parser.add_argument("--all-labels", type=Path, help="labels for every artifact, for the prompting pairs")
    args = parser.parse_args()
    table = [row for path in args.verdicts for row in rows_of(path)]
    with args.labels.open() as stream:
        labels = [r for r in csv.DictReader(stream) if r["verification_stage"] == "accepted" and r["analysis_eligible"] == "True"]
    classes = artifacts(table, labels)
    seen = {r["sample"] for r in table}
    missing = [r["sample_id"] for r in labels if r["formal_reliability_state"] == "unfavorable" and r["sample_id"] not in seen]
    if len(missing) > 1 and not args.partial:     # VT0541's only clause is unresolved, so one is expected
        raise SystemExit(f"{len(missing)} rejected artifacts have no clause rows, so the verdict table is incomplete")
    report = {"rq1": rq1(table), "artifacts": dict(Counter(classes.values())), "rq3": rq3(classes, labels, table)}
    if args.all_labels:
        with args.all_labels.open() as stream:
            everything = [r for r in csv.DictReader(stream) if r["analysis_eligible"] == "True"]
        report["concordance"] = concordance([
            {"workflow": r["workflow"], "model": r["model"], "shot": r["shot"], "accepted": r["verification_stage"] == "accepted",
             "original": r["formal_reliability_state"] == "favorable", "certified": classes.get(r["sample_id"]) in ("Clean", "Sound")}
            for r in everything])
    if args.rq2:
        report["rq2"] = rq2(rows_of(args.rq2))
    if args.rq5:
        arms = [{**r, "arm": r["label"].split("|")[0]} for r in rows_of(args.rq5)]
        hidden = set(args.hidden.read_text().split())
        tasks = args.rq5_tasks.read_text().split()
        pool = args.rq5_pool.read_text().split()
        share = sum(t in hidden for t in pool) / len(pool)
        report["rq5"] = rq5(arms, hidden, tasks, share)
        for path in args.drop or []:
            kept = [t for t in tasks if t not in set(path.read_text().split())]
            report[f"rq5_without_{path.stem}"] = rq5(arms, hidden, kept, share)
    if args.rq4_verdicts:
        haiku = rows_of(args.rq4_verdicts)
        for row in haiku:
            row["sample"] = row.get("sample") or row["label"]
        tasks = args.rq4_tasks.read_text().split()
        report["rq4"] = rq4(rq4_attempts(table, labels, haiku, rows_of(args.rq4_stages), tasks))
        for path in args.drop or []:
            kept = [t for t in tasks if t not in set(path.read_text().split())]
            report[f"rq4_without_{path.stem}"] = rq4(rq4_attempts(table, labels, haiku, rows_of(args.rq4_stages), kept))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "tables.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("rq1", "artifacts")}, indent=1))


if __name__ == "__main__":
    main()
