# The `tasks_fair20.csv` task set

`results/tasks/tasks_fair20.csv` holds 20 VerusEval tasks used to run Claude Haiku 5.5 through the paper's StarVerus few-shot workflow. "Fair" here means the tasks are not known to be broken. It does not mean the sample is representative, and it does not mean the references are free of hidden requirements. Half of them are not.

## How it was derived

[`analysis/sample_fair20.py`](../analysis/sample_fair20.py) rebuilds the list from the release's labels and confirms an exact match with the committed file. The list was first produced on 26 October 2026.

| Step | Tasks left |
|---|---|
| Tasks in the paper's catalog | 762 |
| Has an eligible StarVerus few-shot artifact from DeepSeek-Chat, DeepSeek-Reasoner and Qwen3-Coder | 744 |
| Not on the broken-task list | 568 |
| Not already run in `haiku-5` or `haiku-hard-1` | 565 |
| No strong model scored clean on it | 289 |
| Random sample, `random.Random(20261026).sample(pool, 20)` on the sorted pool | 20 |

The broken-task list is the 148 tasks whose reference uses a numeric constant other than 0, 1 or 2 that never appears in the model's input, plus the 36 references the paper's own review marked defective. That makes 176 tasks, with 8 in both groups.

The run was stopped after 6 tasks on 26 October, then completed on 1 November with the same model and code. Every task has one Haiku result, so the stop did not filter the sample. The results are in `results/claude-runs/haiku-fair20` and `haiku-fair20-rest`.

## What the filters do not give you

**The pool is enriched for failures.** The 276 tasks a strong model scored clean on were removed on purpose, because the question at the time was whether the evaluator's flags hold up. Each of the 20 was flagged, or failed to verify, for all three strong models. So the sample cannot estimate how a model or the evaluator does across the benchmark. Comparing Haiku's 20 of 20 with the original models' 8 to 13 is also biased in Haiku's favor, because the tasks were selected on those models' failures.

**Hidden requirements remain.** The broken-task tagger only sees numeric constants. It misses "the input is non-empty", and it ignores 0, 1 and 2, so it also misses `x >= 0`.

## Audit of the 20

None of the 20 inputs contains a `requires` or `ensures` clause or a comment. The model gets executable code and, on some tasks, example calls in `main`. Every reference precondition is therefore something the model has to infer.

For 10 tasks the reference precondition is stricter than the one in Haiku's verified contract. [`analysis/refute_preconditions.py`](../analysis/refute_preconditions.py) confirms each one without a model. It finds a concrete input for which Verus proves that Haiku's precondition holds and the reference's fails. All 10 are refuted, and none is vacuous. As a control, the same search found no witness on the 5 `pre_ref_to_gen` checks, which hold. The output is in [`results/tasks/fair20_refutations.txt`](../results/tasks/fair20_refutations.txt).

| Task | Function | Reference clause absent from the input | Witness |
|---|---|---|---|
| `DAFNY2VERUS-COLLECTION_42` | `reverse` | `a.len() > 0` | `a` empty |
| `MBPP-verified_task_72` | `is_sub_array` | `sub.len() <= main.len()` | `main` empty, `sub` length 1 |
| `VeriCoding_VA0115_vericoded` | `solve` | `valid_input(a)` | `a == -1` |
| `VeriCoding_VA0625_vericoded` | `determine_food_safety` | `x >= 0` | `x == -1` |
| `VeriCoding_VD0367_vericoded` | `yarra` | `arr.len() > 0` | `arr` empty |
| `VeriCoding_VT0026_vericoded` | `meshgrid` | `x.len() > 0`, `y.len() > 0` | both empty |
| `VeriCoding_VT0178_vericoded` | `ix_` | `seq1.len() > 0`, `seq2.len() > 0` | both empty |
| `VeriCoding_VT0376_vericoded` | `chebyshev` | `coef.len() > 0` | `coef` empty |
| `VerusBench_Diffy_condm` | `myfun` | `N > 0` | `N == 0`, `a` empty |
| `VerusBench_MBPP_task_id_262` | `split_array` | `list@.len() > 0`, `0 < l` | `list` empty, `l == 0` |

On these 10 tasks a clean score requires the model to add a restriction that its own verified contract shows the code does not need. Nine of them also fail the I/O suite's invalid-input cases for the same reason. The model could guess the restriction from the example calls, but it cannot derive it from the code.

The remaining 10 tasks split as follows. An unresolved I/O check is incomplete in the paper's terms, not a flag, so 14 of the 20 are flagged, 4 are incomplete and 2 are clean. All of these results use the guarded comparison.

| Result on Haiku's contract | Tasks |
|---|---|
| Clean | 2: `HumanEval-Verus_task_63`, `VerusBench_MBPP_task_id_18` |
| Incomplete: formal check passes, I/O check unresolved | 4: `MBPP-verified_task_36`, `VeriCoding_VT0048`, `VT0111`, `VT0457` |
| Flagged: stronger postcondition than the reference, I/O check unresolved | 1: `VeriCoding_VT0187` |
| Flagged: guarded `post_gen_to_ref` rejected, then proved by the adjudicator | 3: `VeriCoding_VD0578`, `VH0074`, `VerusBench_MBPP_task_id_807` |

## What the set does support

A correct contract is reachable from the input alone on all 20 tasks, because Haiku produced one. Here correct means Verus accepted the program, both reliability directions hold (reference precondition implies Haiku's, and Haiku's postcondition implies the reference's under both preconditions, which is weaker than the unconditional form the paper's labels use), and no valid or wrong-output I/O case failed. The hidden clauses above make the contract more general than the reference, which is the safe direction.

So the accurate description is this. On the guarded comparison, these 20 tasks are solvable from the given code, and half of them cannot be scored clean without matching a precondition the input never states. On the paper's unconditional L2, 7 of the 20 are still rejected on a first attempt (`MBPP-verified_task_72`, `VeriCoding_VA0115`, `VD0578`, `VH0074`, `VT0026`, `VT0178`, `VerusBench_MBPP_task_id_807`), and those are undecided, so this claim does not yet extend to that form. As the authors point out, a clause the code does not need may still be a requirement of the original task, which this audit has not checked.

## Limits

- Twenty tasks, one Haiku run each, drawn from a failure-enriched pool. The 10 of 20 rate does not carry over to the 762 tasks.
- The audit covers preconditions only. Where `post_ref_to_gen` is reported invalid, it is unresolved, but it would only mean Haiku's postcondition is stronger.
- Reliability relies on the adjudicator's Verus proofs and the evaluator's guarded re-run, not on the paper's unconditional L2, and 6 tasks have an unresolved I/O check.
- The refuter's search is small: sequence lengths 0 to 2, a few integers and at most 40 inputs per check. Finding no witness proves nothing.
