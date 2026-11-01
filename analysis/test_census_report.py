"""Known-answer test for census_report, on synthetic rows.

    python3 -I analysis/test_census_report.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_report import CLASSES, artifacts, clause_class, paired_bootstrap, rq1, rq3, rq4

P, R, U = {"verdict": "proved"}, {"verdict": "refuted"}, {"verdict": "undecided"}
C = {"verdict": "refuted", "computed": True}


def clause(sample, guarded, uncond, direction="L2"):
    return {"sample": sample, "direction": direction, "guarded": guarded, "uncond": uncond}


EXPECTED = [
    (clause("a|m|s|t", R, R), "Difference"),
    (clause("a|m|s|t", R, R, "L1"), "Difference"),
    (clause("b|m|s|t", P, R), "Premise only"),
    (clause("c|m|s|t", P, P), "Solver limit"),
    (clause("d|m|s|t", P, U), "Guarded only"),
    (clause("e|m|s|t", U, R), "Certified false, unlocated"),
    (clause("f|m|s|t", P, C), "Computed"),
    (clause("g|m|s|t", U, C), "Computed"),
    (clause("h|m|s|t", U, U), "Undecided"),
]
for row, want in EXPECTED:
    assert clause_class(row) == want, (row, want)

table = [row for row, _ in EXPECTED]
one = rq1(table)
assert one["clauses"] == 9 and sum(one["classes"].values()) == 9 and set(one["classes"]) == set(CLASSES)
assert one["classes"]["Difference"] == 2 and one["classes"]["Computed"] == 2 and one["impossible_cell"] == 0
assert rq1([clause("x|m|s|t", R, P)])["impossible_cell"] == 1

labels = [{"sample_id": s, "triviality_state": t, "io_state": i} for s, t, i in [
    ("a|m|s|t", "favorable", "favorable"), ("b|m|s|t", "favorable", "favorable"), ("c|m|s|t", "favorable", "unfavorable"),
    ("d|m|s|t", "favorable", "favorable"), ("e|m|s|t", "unfavorable", "favorable"), ("z|m|s|t", "favorable", "favorable")]]
classes = artifacts(table, labels)
assert classes == {"a|m|s|t": "Difference", "b|m|s|t": "Sound", "c|m|s|t": "Sound", "d|m|s|t": "Undecided",
                   "e|m|s|t": "Trivial", "z|m|s|t": "Clean"}
three = rq3(classes, labels, table)
assert three["io_passing"] == 5 and three["io_passing_with_rejection"] == 4
assert three["outcome"] == {"Difference": 1, "Sound": 1, "Undecided": 1, "Trivial": 1}

tasks = [f"t{i}" for i in range(10)]
haiku = dict(zip(tasks, ["Clean"] * 6 + ["Sound"] * 2 + ["Undecided", "Not verified"]))
old = dict(zip(tasks, ["Clean"] * 2 + ["Difference"] * 3 + ["Not verified"] * 5))
four = rq4({"haiku-5-5": haiku, "gpt-4o": old})
assert four["haiku-5-5"] == {"tasks": 10, "verified": 9, "sound_low": 8, "sound_high": 9, "difference": 0, "undecided": 1, "trivial": 0}
assert four["gpt-4o"]["verified"] == 5 and four["gpt-4o"]["sound_low"] == 2
low, high = four["gpt-4o"]["haiku_minus_model_sound"]
assert 0 < low <= 0.6 <= high
assert paired_bootstrap([1] * 20, [1] * 20) == (0, 0)
print("all known answers match")
