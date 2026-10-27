# VerusEval and VeruSteer re-check

An independent re-check of [VerusEval: Evaluating LLM-Generated Verus Specifications Beyond Verifier Acceptance](https://arxiv.org/abs/2610.26464) (Wang et al., 2026), built on the authors' released artifact ([lifetruthuu/VerusEval](https://github.com/lifetruthuu/VerusEval), v1.0.0). The release reproduced the paper's tables exactly, which is what made this possible.

The question: when the evaluator flags a verified contract as wrong, is the contract actually wrong?

A second part, in [`verusteer/`](verusteer), re-checks the same group's [VeruSteer](https://arxiv.org/abs/2610.29755). About 69% of its repair failures cannot be fixed under the pipelines' own rules. In 73% of failed runs the program never changes at all. On 30 failing tasks, a Haiku 5.5 agent with Verus in a shell got 10 accepted where the pipeline running the same model got 6, and it flagged 9 contracts as false along the way.

## Findings

**1. The evaluator records "could not prove" as "false".** In `metrics_rebuild/share/lemma_implication.py`, `_classify_verus_run` maps Verus's `postcondition not satisfied` to `holds: False, status: "invalid"`. That message means the SMT solver did not find a proof within the 20 s budget. Implications that need induction, `bit_vector`, nonlinear arithmetic or a u8/char bridge come out "invalid" even when they hold. [`proofs/`](proofs) contains Verus proofs of four such implications (`HumanEval-Verus_task_6`, `VeriCoding_VT0256`, `VA0080`, `VA0515`).

**2. Some references depend on constraints the model never sees.** For example, `VeriCoding_VA0187` requires `n, m <= 100`, `VerusBench_CloverBench_array_copy_strong` requires `a.len() <= 100`, and `VeriCoding_VA0515` requires `-40 <= temp <= 40`. None of these bounds appear in the code given to the model. [`analysis/broken_tasks.py`](analysis/broken_tasks.py) finds 148 tasks whose reference contract uses a numeric constant absent from the input. Adding the 36 references the paper's own review marked defective gives 176 of 762 tasks. This is a lower bound, because non-numeric constraints such as "the input is non-empty" are not detected.

**3. Re-grading 30 of the paper's own flags.** The sample is 30 accepted artifacts from DeepSeek-Chat, DeepSeek-Reasoner and Qwen3-Coder that the evaluator marked weaker than the reference, on tasks outside the broken list, split by spec size ([`analysis/sample_regrade.py`](analysis/sample_regrade.py)). For every invalid check, [`scripts/adjudicate.py`](scripts/adjudicate.py) captures the evaluator's own lemma, splices proof hints into its unchanged body and re-verifies the whole file with Verus. It tries cheap tactics first, then Claude Haiku, Sonnet and Opus. A "proved" verdict is checked by Verus alone.

| Verdict | Big specs | Small specs | Total |
|---|---|---|---|
| Evaluator wrong: implication proved | 9 | 5 | 14 |
| Stricter only on inputs that cannot exist (e.g. `len < usize::MAX`) | 2 | 2 | 4 |
| Real: postcondition too weak | 2 | 4 | 6 |
| Real: precondition rejects inputs the code handles | 2 | 4 | 6 |

[`results/regrade-30/final_verdicts.csv`](results/regrade-30/final_verdicts.csv) gives each verdict and its basis. The 14 "evaluator wrong" rows are machine-checked. Most of the 12 real issues rest on model-proposed counterexamples, which were checked by reading the contract against the code, not by machine.

**4. A current model.** Claude Haiku 5.5 ran through the paper's StarVerus adapter on 12 tasks via the Claude Agent SDK ([`patches/starverus-agent-sdk.patch`](patches/starverus-agent-sdk.patch)). All 12 verified, mostly on the first candidate. The evaluator scored 1 as clean. Ten of the other 11 traced back to finding 1 or 2. The eleventh (`MBPP-verified_task_36`) passed every formal check and was flagged only because its I/O check came back unresolved.

**5. A blind review catches the real issues.** Given only the verified program, with no reference and no flags, Haiku listed under-specified postconditions and over-restrictive preconditions ([`analysis/review_specs.py`](analysis/review_specs.py)). It caught 11 of the 12 real issues above for about $0.03 in total. The StarVerus pipeline reviews a contract only when verification fails.

**6. Most verification failures happen before the proof stage.** In the released labels, 4,804 of 6,578 failures (73%) stop at parsing or the Verus frontend. The workflows give models no compiler access, and StarVerus ranks any candidate that fails to compile below every candidate that compiles. Within a task, artifacts that failed the frontend had larger specs than the accepted ones in 60% of tasks.

[`analysis/released_labels.py`](analysis/released_labels.py) recomputes the paper's headline from its labels. It finds 42.3% of accepted artifacts pass every check under strict equivalence, 52.7% if a contract may be stronger than its reference, and 55.7% with broken tasks removed as well. Trivial specs are 1.5% of accepted artifacts.

## What holds up

The paper's thesis is real. Verified contracts can be weak, and finding 3 includes clear cases: argmax and argmin that leave tie-breaking open, a `to_uppercase` contract that never says non-letters stay unchanged, and an `encrypt` contract weakened by a truncating `as u8` cast. The disagreement is about size. On this sample, most of the evaluator's flags were the evaluator's. The paper's abstract itself notes that a failed comparison does not establish which side is defective.

## Caveats

- Samples are small: 30 re-graded flags and 12 Haiku tasks, six of which came from tasks that every original model failed.
- The adjudicator can only show an implication holds. An unresolved check is "not proved within budget", not "false". Counterexamples are model claims.
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

`run_haiku.py --model claude-sonnet-5-5` runs Sonnet instead. Proofs check with `run verus /path/to/proofs/implications.rs`.

## Layout

- `scripts/`: generation driver, adjudicator, verdict classifier, summary
- `analysis/`: statistics from the released labels, broken-task tagger, re-grade sampler, blind review
- `proofs/`: hand-written Verus proofs for findings 1 and 4
- `patches/`: the StarVerus change that routes model calls through the Agent SDK
- `results/claude-runs/`: Claude-generated programs, usage, adjudications and verdicts per run (`haiku-fair20` was stopped after 6 of 20 tasks)
- `results/regrade-30/`: sample IDs, adjudications, final verdicts, blind reviews
- `results/tasks/`: task lists, including the broken-task lists
- `verusteer/`: the VeruSteer re-check, with its own README

The release's programs, references and per-file records are referenced by sample ID and not redistributed here. Scripts are MIT licensed. The patch modifies MIT-licensed code from the StarVerus baseline bundled with VerusEval.
