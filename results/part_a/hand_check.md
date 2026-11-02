# Hand check of the failure rule

60 failures sampled with seed 20261102 and read by Claude, not by a person, against the rule in `analysis/part_a.py`. The rule matched on 56 of 60 (93.3%).

| Sample | Rule said | Reading | Why |
|---|---|---|---|
| 3 | Verus-specific | General Rust | an undeclared variable inside a quantifier |
| 44 | Verus-specific | General Rust | an undeclared variable in a clause |
| 26 | General Rust | Verus-specific | `result` used in `ensures` with no named return, which is Verus syntax |
| 37 | General Rust | Verus-specific | the same as sample 26 |

The misses run both ways, so the share is roughly unbiased on this sample. The rule was not changed after reading them.
