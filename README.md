# VerusEval and VeruSteer re-check

An independent re-check of [VerusEval: Evaluating LLM-Generated Verus Specifications Beyond Verifier Acceptance](https://arxiv.org/abs/2610.26464) (Wang et al., 2026), built on the authors' released artifact ([lifetruthuu/VerusEval](https://github.com/lifetruthuu/VerusEval), v1.0.0). The release reproduced the paper's tables exactly, which is what made this possible.

The question: when the evaluator flags a verified contract, is the contract actually wrong?

A second part, in [`verusteer/`](verusteer), re-checks the same group's [VeruSteer](https://arxiv.org/abs/2610.29755). About 69% of its repair failures cannot be fixed under the pipelines' own rules. In 73% of failed runs the program never changes at all. On 30 failing tasks, a Haiku 5.5 agent with Verus in a shell got 10 accepted where the pipeline running the same model got 6, and it flagged 9 contracts as false along the way.

> **Correction, 1 November 2026.** Findings 3 and 4 overstated what the adjudicator shows. It proves a guarded postcondition comparison, with both preconditions in the antecedent. The paper's released labels use an unconditional comparison, which the paper documents as a deliberate choice. A proof of the guarded form does not discharge the obligation the paper reported. The paper also says plainly that a rejected obligation is a failed proof attempt, not a confirmed difference, so it does not claim these flags are defects. Details are in finding 3, and the [authors' reply](https://github.com/Dominik-O22/veruseval-recheck/issues/2) is summarized below.

## Findings

**1. The evaluator records "could not prove" as "false".** In `metrics_rebuild/share/lemma_implication.py`, `_classify_verus_run` maps Verus's `postcondition not satisfied` to `holds: False, status: "invalid"`. That message means the SMT solver did not find a proof within the budget, and the paper itself treats such a result as a failed proof attempt, not a confirmed difference. Its headline still counts these as flags. Implications that need induction, `bit_vector`, nonlinear arithmetic or a u8/char bridge come out "invalid" even when they hold. [`proofs/`](proofs) contains Verus proofs of four such implications (`HumanEval-Verus_task_6`, `VeriCoding_VT0256`, `VA0080`, `VA0515`). These hold in the paper's unconditional form: [`proofs/splice_unconditional.py`](proofs/splice_unconditional.py) splices them into harnesses from the evaluator's guarded path with the premises removed, and Verus accepts all five lemmas. This covers L2 only, on Haiku's artifacts.

**2. Some references depend on constraints the model never sees.** For example, `VeriCoding_VA0187` requires `n, m <= 100`, `VerusBench_CloverBench_array_copy_strong` requires `a.len() <= 100`, and `VeriCoding_VA0515` requires `-40 <= temp <= 40`. None of these bounds appear in the code given to the model. [`analysis/broken_tasks.py`](analysis/broken_tasks.py) finds 148 tasks whose reference contract uses a numeric constant absent from the input. Adding the 36 references the paper's own review marked defective gives 176 of 762 tasks. This is a lower bound, because non-numeric constraints such as "the input is non-empty" are not detected.

**3. Re-grading 30 of the paper's own flags.** The sample is 30 accepted artifacts from DeepSeek-Chat, DeepSeek-Reasoner and Qwen3-Coder that the evaluator marked weaker than the reference, on tasks outside the broken list, split by spec size ([`analysis/sample_regrade.py`](analysis/sample_regrade.py)). For every invalid check, [`scripts/adjudicate.py`](scripts/adjudicate.py) captures the evaluator's own lemma, splices proof hints into its unchanged body and re-verifies the whole file with Verus. It tries cheap tactics first, then Claude Haiku, Sonnet and Opus. A "proved" verdict is checked by Verus alone, but see the correction below for which lemma it proves.

| Verdict | Big specs | Small specs | Total |
|---|---|---|---|
| Passes the guarded comparison | 9 | 5 | 14 |
| Stricter only on inputs that cannot exist (e.g. `len < usize::MAX`) | 2 | 2 | 4 |
| Real: postcondition too weak | 2 | 4 | 6 |
| Real: precondition rejects inputs the code handles | 2 | 4 | 6 |

[`results/regrade-30/final_verdicts.csv`](results/regrade-30/final_verdicts.csv) gives each verdict and its basis, and still uses the old `checker_wrong` label for the first row. Most of the 12 real issues rest on model-proposed counterexamples, which were checked by reading the contract against the code, not by machine.

**Correction.** The 14 rows do not show the evaluator was wrong about the obligation it reported. All 14 have a rejected postcondition comparison in the released labels, and `target_evaluation.postcondition_premise_policy` is `no_preconditions` on every accepted record. The adjudicator re-runs the release's `semantic_strength.py`, which adds both preconditions to the antecedent. Seven rows pass that guarded form with no proof at all, and seven needed a model proof of the guarded form. Across the release, 537 of 1,761 rejected L2 checks and 405 of 2,033 rejected L4 checks were valid under the older guarded form. So a large share of postcondition rejections come from a documented premise policy, not from solver limits.

Re-running L2 unconditionally with no proofs ([`analysis/unconditional_l2.py`](analysis/unconditional_l2.py)) reproduces the released label on all 30 target functions, and all 14 rows stay rejected. A 31st check is a helper function with no released label. Whether those 14 are provable in the paper's form is still open. The authors verified a counterexample for one of them, `MBPP-verified_task_73`, on an input the reference precondition excludes.

**4. A current model.** Claude Haiku 5.5 ran through the paper's StarVerus adapter on 12 tasks via the Claude Agent SDK ([`patches/starverus-agent-sdk.patch`](patches/starverus-agent-sdk.patch)). All 12 verified, mostly on the first candidate. The evaluator scored 1 as clean. Ten of the other 11 traced back to finding 1 or 2. The eleventh (`MBPP-verified_task_36`) passed every formal check with an unresolved I/O check, which the paper counts as incomplete, not flagged. These runs used `scripts/reevaluate.py`, which applies the guarded comparison, so they are not directly comparable with the released labels.

A second run covers the 20 tasks in [`tasks_fair20.csv`](results/tasks/tasks_fair20.csv), a seeded sample of non-broken tasks that no strong original model scored clean on ([how it was derived](docs/fair20-task-set.md)). All 20 Haiku programs verified, against 8 to 13 of 20 for the original few-shot programs (Qwen3-Coder has 11 of the 18 in the release), though selecting on those models' failures biases that comparison in Haiku's favor. On the guarded comparison, 2 of the 20 are clean, 4 are incomplete, and 14 are flagged. After adjudication of the guarded form, none of those is a candidate real miss. On the paper's unconditional L2, 7 of the 20 tasks are still rejected on a first attempt on L2, so that result is limited to the guarded form. On 10 tasks the reference's precondition is stricter than Haiku's verified one, which Verus confirms with a concrete witness and which the numeric tagger in finding 2 cannot see. As the authors note, that does not by itself make the clause unjustified, because it may be a requirement of the original task.

**5. A blind review catches the real issues.** Given only the verified program, with no reference and no flags, Haiku listed under-specified postconditions and over-restrictive preconditions ([`analysis/review_specs.py`](analysis/review_specs.py)). It caught 11 of the 12 real issues above for about $0.03 in total. The StarVerus pipeline reviews a contract only when verification fails.

**6. Most verification failures happen before the proof stage.** In the released labels, 4,804 of 6,578 failures (73%) stop at parsing or the Verus frontend. As the authors note, these are final outputs, after each workflow's own feedback and repair steps, so models do see Verus errors through those steps. StarVerus ranks any candidate that fails to compile below every candidate that compiles. Within a task, artifacts that failed the frontend had larger specs than the accepted ones in 60% of tasks.

[`analysis/released_labels.py`](analysis/released_labels.py) recomputes the paper's headline from its labels. It finds 42.3% of accepted artifacts pass every check under strict equivalence, 52.7% if a contract may be stronger than its reference, and 55.7% with broken tasks removed as well. Trivial specs are 1.5% of accepted artifacts.

## Authors' response

The authors [replied](https://github.com/Dominik-O22/veruseval-recheck/issues/2) on 1 November 2026. They pointed out that a proof of the guarded comparison does not establish L2 or L4, agreed that `invalid` is a misleading label and will consider renaming it, and called the constant scan a useful complementary signal that still needs the original task requirements. They clarified that an unresolved I/O check is incomplete and that the 1 of 12 result measures flag-free artifacts, not correct contracts. They also noted that the failure counts in finding 6 are final outputs, after each workflow's feedback and repair steps, and they supported adding specification review after verification.

## What holds up

The paper's thesis is real. Verified contracts can be weak, and finding 3 includes clear cases: argmax and argmin that leave tie-breaking open, a `to_uppercase` contract that never says non-letters stay unchanged, and an `encrypt` contract weakened by a truncating `as u8` cast. The disagreement is about size. On this sample, about half of the flags clear once the comparison is guarded, and whether the unconditional form or the guarded one is the right standard is a judgment the paper makes openly. The paper's abstract itself notes that a failed comparison does not establish which side is defective.

## Caveats

- Samples are small: 30 re-graded flags, 12 Haiku tasks in finding 4, six of which came from tasks that every original model failed, and 14 more that complete the 20 on the `tasks_fair20.csv` sample. Each Haiku task ran once.
- The adjudicator can only show the guarded implication holds. An unresolved check is "not proved within budget", not "false". Counterexamples are model claims.
- The "broken task" tagger is a heuristic.
- The Agent SDK runs give the model no tools, matching the original harness. Few-shot examples are inlined into one prompt, and temperature is not forwarded.

## Reproducing

You need the VerusEval release (code and data archives, see its `downloads/README.md`), podman or Docker, and, for the model steps, a Claude login (`claude setup-token`, exported as `CLAUDE_CODE_OAUTH_TOKEN`) or an API key. The analysis scripts need only Python 3.

```bash
# In the extracted release root
patch -p1 < /path/to/veruseval-recheck/patches/starverus-agent-sdk.patch
mkdir -p haiku && cp /path/to/veruseval-recheck/{scripts,analysis}/*.py /path/to/veruseval-recheck/Containerfile haiku/
podman build -t veruseval:artifact .
podman build -t veruseval:haiku -f haiku/Containerfile haiku

# Statistics from the released labels (no model calls)
python3 haiku/broken_tasks.py --release . --out results/tasks
python3 haiku/released_labels.py --release . --tasks results/tasks

# Generate with Haiku 5.5 on five tasks, then evaluate, adjudicate and classify
run() { podman run --rm -e CLAUDE_CODE_OAUTH_TOKEN -v "$PWD":/workspace -w /workspace veruseval:haiku "$@"; }
cp /path/to/veruseval-recheck/results/tasks/tasks.csv haiku/
run python haiku/run_haiku.py --limit 5 --output-root runs/haiku-5
run python haiku/adjudicate.py runs/haiku-5 --label haiku-5-5
run python haiku/verdicts.py runs/haiku-5 --label haiku-5-5

# Re-grade the paper's own flags
python3 haiku/sample_regrade.py --release . --tasks results/tasks --run runs/regrade-30
run python haiku/adjudicate.py runs/regrade-30
run python haiku/verdicts.py runs/regrade-30
run python haiku/review_specs.py runs/regrade-30 > runs/regrade-30/haiku_review.jsonl
```

`analysis/sample_fair20.py` rebuilds `tasks_fair20.csv`, and `analysis/refute_preconditions.py` runs in the container like the other `haiku/` scripts.

`run_haiku.py --model claude-sonnet-5-5` runs Sonnet instead. Proofs check with `run verus /path/to/proofs/implications.rs`.

## Layout

- `scripts/`: generation driver, adjudicator, verdict classifier, summary
- `analysis/`: statistics from the released labels, broken-task tagger, re-grade sampler, blind review, `tasks_fair20.csv` sampler, precondition refuter
- `docs/`: how the `tasks_fair20.csv` set was derived, with an audit of its 20 tasks
- `proofs/`: hand-written Verus proofs for findings 1 and 4, and a script that splices them into unconditional harnesses
- `patches/`: the StarVerus change that routes model calls through the Agent SDK
- `results/claude-runs/`: Claude-generated programs, usage, adjudications and verdicts per run (`haiku-fair20` was stopped after 6 of 20 tasks, and `haiku-fair20-rest` is the other 14)
- `results/regrade-30/`: sample IDs, adjudications, final verdicts, blind reviews
- `results/tasks/`: task lists, including the broken-task lists
- `verusteer/`: the VeruSteer re-check, with its own README

The release's programs, references and per-file records are referenced by sample ID and not redistributed here. Scripts are MIT licensed. The patch modifies MIT-licensed code from the StarVerus baseline bundled with VerusEval.
