# Paper plan: what does a VerusEval score measure?

## The question

A VerusEval score looks like a measure of how well models write contracts. This paper asks how much of it is that, and how much comes from setup, from Verus fluency, from what the model was never told, and from the limits of the checker. Of 13,659 attempts, 7,081 verify (51.8%) and 2,995 pass all three checks (21.9%), all measured from released labels. We trace where the rest go.

| Part | Question | Data | Status |
|---|---|---|---|
| A | How much loss comes from setup and Verus fluency? | Released labels, no model | To do |
| B | Do the results carry over to a current model? This is RQ4 below | Haiku 5.5 on 100 random tasks | Built |
| C | How much comes from requirements the model cannot know? This is RQ5 below | Haiku with and without task text | To do |
| D | What are the rejected checks really? This is RQ1 to RQ3 below | The census | Built |

**Part A.** Verified rate by workflow, model and prompting, from 5.5% to 88.5% across the 18 configurations, and the share of variation each explains. Failures before proving, 4,804 of 13,659, sorted by a fixed rule on the diagnostic into general Rust errors, Verus-specific errors and malformed output. The authors point out these are final outputs after each workflow's repair steps, and we report them that way.

Measured with `analysis/part_a.py`: by that rule, 3,811 of the 4,804 are Verus-specific (79.3%), 541 general Rust (11.3%) and 452 malformed (9.4%). A read of 60 by Claude agreed with the rule on 56, with misses both ways. One mistake, indexing with `usize` where Verus needs `int` in a specification, is the first error in 902 attempts (6.6% of all attempts). Only the first error is counted, so fixing it might reveal others. Few-shot prompting raises verified rate by 17 to 51 points across the 9 matched pairs. Taken one at a time, task explains 25.0% of the variation in verified, prompting 10.6%, workflow 8.1% and model 6.8%. The factors overlap, so these shares do not add up.

**Few-shot examples.** Each few-shot run gets five neighbouring tasks with their verified solutions, and 758 of the 762 solution files match the benchmark's references (measured). A task never sees its own solution. On StarVerus artifacts that verified, L3 and L4 clean rises from 16.6% to 34.7% with examples on hidden-constant tasks, and from 59.0% to 60.2% on the others (measured, correlation only). On 84 of 140 hidden-constant tasks every constant appears somewhere in the five examples, which is an upper bound because small numbers match by chance. So examples may teach Verus and also hand over a sibling's limits. On the 2,172 pairs where one configuration verified a task with and without examples, examples lower rejection on all four directions: L1 12.1% to 6.5%, L2 28.3% to 20.4%, L3 31.2% to 25.8%, L4 28.3% to 25.7% (measured). These are first-attempt labels on tasks both verified, and a closer match to the reference is what borrowed answers would also produce.

**RQ5, unknowable requirements.** In the paper's setup the model receives a Rust function with no specification and no task description, and the only comment in any of the 762 inputs is the `// verus!` closing marker, on 89 of them (measured). References carry intent from elsewhere: `VA0187` requires `n, m <= 100`, which its code does not show. Fairness and genuineness are different questions. A limit can be a real task requirement and still be unfair to judge a model on when it was never given.

Public task text exists for 435 of 762 tasks: VeriCoding 243, MBPP 154 and HumanEval 38, of which 369 are outside the development set (measured). Run Haiku through the same StarVerus prompts and generator on the same tasks, one candidate taken as generated, in four arms: with and without the text, each with and without the five worked examples. Text is added as a comment at the top of the input so the pipeline does not change. The zero-shot arms are needed because the examples are themselves a source of hidden knowledge, as below. The sample is in `results/tasks/rq5_tasks.txt`, 50 hidden-constant and 50 other tasks, drawn with seed 20261102 from those 369. Labels come from `analysis/rq5_labels.py`, the release's own unconditional path, which matched the released label on 480 of 480 comparisons across 120 development artifacts. Report paired differences in verified rate and in each of L1 to L4, mainly L3, for all tasks and for each stratum: text with examples, text without examples, and examples without text. The last is also the first test of Haiku with no guide, and it speaks to whether a newer model already knows Verus. The originals verify 26% to 65% on StarVerus zero-shot. A task that fails to verify counts as not passing. No proofs are attempted here, so these are first-attempt labels and a rejection stays a failed attempt.

The StarVerus prompt tells models that specifications "must accurately describe the intended behavior of each function", and its input carries none.

Predictions, logged now and scored afterward: text raises L3 pass rate on the other tasks. On hidden-constant tasks it helps less, because the limit is often not in the text. Effect on verified rate is small. Haiku with no examples verifies above the originals' best zero-shot rate of 64.9% (guesses from reading the inputs, and 5 dry-run tasks show nothing either way).

A rough scan found that on 66 of 78 hidden-constant tasks with text, not all of the reference's constants appear in the text. The scan also catches type bounds, so it overstates. If the limit is not in the text either, no reader could have known it. Report these separately after reading a sample.

The I/O suites do not give an independent check, because the paper says they "rest on the same reference as specification correctness". So the I/O and contract checks both depend on the reference. The third check, triviality, looks at the generated contract alone and flags 104 of 7,081. We say so.


Status: revision 7, 2 November 2026, frozen as `freeze-2`, reframed on Dom's decision. `freeze-1` holds revision 6. Earlier: two rounds of adversarial review and the original authors' [reply](https://github.com/Dominik-O22/veruseval-recheck/issues/2). Current state, gates and spending are in [`docs/status.md`](status.md). Numbers marked measured come from the VerusEval release or this repo, and numbers marked guess are planning assumptions.

## Part D in one paragraph

VerusEval (arXiv 2610.26464) compares LLM-written Verus contracts with references. Its authors say plainly that "A rejected obligation is a failed proof attempt, not a confirmed semantic difference." That leaves thousands of comparisons undecided. This paper decides as many as it can. For each rejected soundness lemma on the 2,166 accepted artifacts that have one, it produces a Verus-checked proof or a concrete counterexample, under the paper's unconditional comparison and under a guarded one that assumes both preconditions. The result is a certified account of what those rejections are, plus a reusable grader.

Working title: *What Does a VerusEval Score Measure?* The final title should state the measured result.

This is a re-measurement, not a reproduction, and we do not claim that the paper's findings fail. We report what certification adds and let the numbers stand.

## What the original paper says

We use its terms. L1 is reference precondition implies generated precondition. L2 is generated postcondition implies reference postcondition. These are the soundness directions, and L3 and L4 are the completeness converses. Its "unresolved" means an attempt that did not complete, so ours is called **Undecided**.

We credit the following directly.

- "A rejected obligation is a failed proof attempt, not a confirmed semantic difference."
- Its percentages are "not a confirmed distribution of semantic defects".
- 55.0% of flagged artifacts rest only on rejected implications.
- 3,790 artifacts are flagged, 296 more are unflagged but incomplete, and it reports 46.5% if those count as passing.
- Postcondition comparisons deliberately carry no precondition premises. Its own `min_array` note says an artifact fails L2 "only because the postcondition comparison does not assume |a| > 0".
- Higher acceptance "does not consistently come with" higher correctness. The word "consistently" matters, and the paper notes that prompting moves both together.

The 2,370 rejected obligations are a gap the paper describes and leaves open. It is not an error we are correcting.

The authors reviewed an earlier re-check and confirmed the two forms: their reported L2 and L4 are unconditional, and a guarded proof does not establish them. Their example is `MBPP-verified_task_73`, where the generated postcondition permits `result = true` at `n = 0`, an input the reference precondition excludes. They verified that counterexample in Verus. That is a Premise only case below. They also agreed that the `invalid` label is misleading.

## Research questions

**RQ1, what the rejections are.** For each rejected L1 and L2 lemma, what does certification find under each comparison form?

**RQ2, stricter references.** On how many tasks outside the 148 numeric-list tasks does a sound, same-code contract show that the reference's precondition rejects inputs the code handles, and is that restriction stated in the original task?

**RQ3, what changes.** Descriptive only. How do I/O screening and the configuration comparisons look once rejections are certified?

**RQ4, a current model.** On a random sample of tasks, how do contracts from Claude Haiku 5.5 compare with the original models' once rejections are certified? The aim is to test whether the paper's results carry over to current models. We chose Haiku because it is the same class of model as the originals, not a frontier model.

## Out of scope

The workflow experiment becomes a separate note. VeruSteer's result is a replay-only selector gain, and its paper says that design "does not describe an end-to-end benchmark". Requirements for that note, from review: one agent harness for both models, no shared host mount, a calibration arm on the released pipeline, pinned spec fns, an AST-based bypass check, zero acceptance on frozen-unfixable trees as a negative control, runs keyed by `tree_id`, no token cap, arms interleaved by tree, and the 30 pilot trees excluded.

Also out: `tasks_fair20.csv`, the 12 Haiku tasks, the blind-review finding, the frontend failure statistics, and any ranking among the original models. They stay in the repo as exploratory. L3 and L4 stay out of the census, which means this paper cannot retest the 63.2% equivalence figure, and it says so.

## Population

| Item | Size | Source |
|---|---|---|
| Accepted artifacts | 7,081 | measured |
| Rejected L1, L2 obligations | 609, 1,761 | measured |
| Rejected clause lemmas, L1, L2 | 723, 2,320 (3,043 total) | measured |
| Accepted artifacts with a rejected L1 or L2 | 2,166 on 541 tasks. One, `StarVerus|llama|few-shot|VeriCoding_VT0541_vericoded`, has an unresolved clause and no rejected clause lemma, so the census covers 2,165 | measured |
| All artifacts with a rejected L1 or L2 | 4,365 | measured |
| Rejected L2 valid under the older guarded form | 537 of 1,761 | measured |
| Rejected L2 with no real precondition on either side | 369 | reviewer measured |
| Tasks with a rejected L3 outside the numeric list | 182 | reviewer measured |

The unit is the clause lemma, because that is what the labels record. An obligation is proved when every rejected clause lemma is proved, and refuted when any is.

The census covers accepted artifacts only. The other 2,199 artifacts with rejections failed verification, and regrading a contract the verifier rejected would answer a different question. That choice affects RQ3, which accounts for it.

## The grader

One rule: only a positive Verus result produces a verdict. A timeout or failed attempt never does.

**Regeneration.** The stored `formal_recheck` harnesses cover 214 artifacts (measured), and those are `proof_failed` artifacts, not this population (reviewer measured). So we regenerate through the release's `metrics/_clause_implication.py` and require the regenerated `obligation_context` and status to match the released record before using a lemma. This is gate 1.

**Two forms.** Unconditional is the paper's form. Guarded adds both preconditions to the antecedent. A guarded refutation is also an unconditional refutation with the same witness, and an unconditional proof is also a guarded proof, so results propagate and each pair needs at most two searches. Where neither side has a real precondition, the two forms are one formula and get one search.

**Proved.** Verus accepts a proof of the unchanged lemma, with no `assume`, `admit`, `external_body` or new `#[verifier]` attribute.

**Refuted.** A proposer returns literal values only. A fixed template, with no loops, branches or calls, binds them and asserts the antecedent and the negated consequent, with `reveal_with_fuel` where needed, following the release's concrete-value engine in `contract_eval.py`, which proves `assert(Q)` or `assert(!Q)`. The same file with `assert(false)` is also run. If that verifies, the context is inconsistent and the verdict is void. Its failure proves nothing and is not used as evidence, so this check can only remove a verdict.

**Computed values.** Some clauses read outside a sequence, and Verus leaves that value unspecified. A witness may then bind a scalar to an expression over values already bound to literals, such as `if v[0] == 0 { 1 } else { 0 }`. The grammar has reads, `==`, `if` and suffixed literals, with no arithmetic or calls, so the pins always have a solution. These witnesses have no single concrete input and are never run. They are reported as their own group, are not counted as Difference or Premise only, and each needs its own reading, because a read of nothing can be noise or a real hole.

**Realizability.** Verus verifies code without running it, so a witness can describe a value no real program builds. `Vec::push` has no length precondition at the pinned version (reviewer read of `vstd`). Four of the 30 pilot artifacts have this shape. So witnesses are also compiled and run where the types allow it, and a difference that exists only on unrepresentable inputs gets its own class.

**Guard check.** A guarded proof means little if the two preconditions cannot hold together. Two of the 537 have a false reference precondition (reviewer measured). A guarded proof counts only with a witness satisfying both preconditions.

Known hard cases, to be measured in the pilot: floats touch 134 obligations and the authors' concrete engine left 31.4% unresolved on them, recursion touches 317, and 54 have `int` or `nat` signatures. Any of these may end as Undecided, which is an acceptable result and is reported by type.

### Primary table

The main result is the 3 by 3 grid of guarded outcome against unconditional outcome, each proved, refuted or undecided. Cells implication rules out stay empty, and that is a check on the grader. Named cells:

| Guarded | Unconditional | Name | Meaning |
|---|---|---|---|
| Refuted | Refuted | Difference | The contracts differ inside both preconditions |
| Proved | Refuted | Premise only | They agree inside both preconditions, and differ outside them |
| Proved | Proved | Solver limit | The paper's own obligation holds |
| Proved | Undecided | Guarded only | Holds with premises, and the premise may only help the solver |
| Undecided | Refuted | Certified false, unlocated | The paper's obligation is certified false |
| Undecided | Undecided | Undecided | Nothing established |

L1 has one form, and refuted means the generated contract rejects an input the reference accepts. 263 of the 609 have no reference precondition, so L1 only asks whether the generated precondition is always true (reviewer measured). Those are reported separately.

None of these labels says which contract is right. A reference can be the side that is off.

### Artifact summary

Obligations are the unit of inference. Artifacts are a summary, in this order: Trivial if the paper's check holds, then Difference if any function has one, then Sound if every L1 and L2 is valid, Solver limit or Premise only, then Undecided. L3 and L4 are untouched, so Sound is not equivalent and not "correct". The paper's own line applies to us: "We do not claim that the generated contract is correct".

## Validation

1. **Authors' variants.** `data/evidence/contract_variants` has 943 retained variants and 395 identity bases (reviewer confirmed the counts and operator mapping). Stronger preconditions and weaker postconditions must be refuted, and weaker preconditions and stronger postconditions must clear.
2. **Hard true cases.** The variant bases are easy, because they were selected as already equivalent. Add the 17 clauses from the `regrade-30` rows, the proofs in `proofs/`, and any others with a checked proof.
3. **Known false cases.** Natural obligations with a failing correct or wrong-output case. These are limited to development tasks, 71 artifacts, because the other cases sit on census tasks and would expose census data before the freeze.
4. **Both engines.** On validation sets only, run prover and refuter on every lemma. Any lemma with both verdicts is a soundness bug and stops the run.
5. **Stability.** Run the frozen grader twice on 200 development lemmas and report the flip rate.

Early signal for gate 1: with the antecedent reduced to the generated postcondition, a no-model rerun reproduced the released L2 label on all 30 target functions (measured). A review run of the release's per-clause path matched context and status on 57 of 57 L2 clauses. Stored hashes can't be used, because digests depend on absolute paths and the Verus binary, and the stored `obligation_sha256` does not match its own stored context. L1 uses a different path and is untested.

Gates, fixed now: zero soundness bugs, at least 90% recall on refutation and on proof for the variants. Recall on the hard sets is reported, because those define the real instrument error. RQ1 is a census, so it has no sampling interval, but instrument error is real and is reported next to every share.

## RQ1 analysis

Report the grid by lemma, form, configuration and type class. Report the search tier that produced each verdict, because shares depend on the prover. Undecided is never counted either way.

Predictions, logged now and scored afterward, with no pass or fail attached. On the 1,909 obligations with no failing I/O case: proved in some form 40%, certified false 35%, Undecided 25% (guess from the pilot's 9 proved, 16 claimed and 1 unresolved of 26, all guarded). Premise-only share of rejected L2: above 20% (guess, because 537 is an upper hint, not a count).

For RQ1 to RQ3 the subjects are DeepSeek, Qwen, GPT-4o and Llama, so Claude is an instrument there and not a subject. RQ4 is the exception, and its analysis says so.

## RQ2 analysis

Unit: task. A task counts when at least one accepted artifact meets all of these: same executable code as the input under the fixed lynette build from microsoft/verus-proof-synthesis#53, all L1 and L2 valid or proved, and an L3 witness the reference rejects. One such artifact is enough, because it shows the code is safe and the contract is sound on that input.

The search is `analysis/rq2_check.py`: same code under the fixed lynette, then the frozen `witness.py` on L3, counting only plain witnesses that compiled and ran.

Reviewer counts outside the numeric list: 159 same-code tasks, 109 with L2 valid, 103 with L1 and L2 valid. So the result is close to known, and RQ2 is an estimate, not a test. 0 of 762 inputs contain `requires` or `ensures` (reviewer measured), and 10 have a non-empty `main` (measured), so nearly all inputs give no signal. The 10 are tagged.

A restriction the code does not need can still be a requirement of the original task, as the authors point out, so a witness alone does not make a clause a defect. Each counted task is therefore checked against its original task statement and labeled stated, unstated, or no statement available. Only unstated restrictions are headlined. Sources are to be confirmed with the authors, and the public HumanEval and MBPP statements cover those subsets.

Comparator: 148 numeric-list tasks. The 36 candidate reference defects are a different construct and are tracked separately. Hand-label a random 60 counted tasks to estimate precision.

## RQ3 analysis

Descriptive, in a fixed order, with no claim that a finding reverses.

1. **Definition-only row first.** With released labels and no proofs, 736, 1,337 or 1,867 artifacts move depending on how I/O is treated (measured). These are redefinitions, reported as such, so they are never mistaken for grader results.
2. **I/O screening.** Among 4,749 I/O-passing artifacts, 78.7% are proved sound on the released labels (measured). Of the 1,012 with a rejected L1 or L2, report how many become proved and how many become certified false. A certified difference on an I/O-passer supports the paper's concern, and we say so. Reporting 78.7% is not a retest of 63.2%, which needs L3 and L4.
3. **Configuration comparisons.** Exploratory. Census coverage correlates with acceptance at 0.907 across configurations (reviewer measured), so relabeling alone tends to raise the acceptance link. We therefore recompute on accepted artifacts only, call that a new estimand, and publish a random-relabel negative control. On the 13 of 14 matched pairs with a clear acceptance gap, report how many are concordant for each metric, original versus certified, with paired bootstrap deltas.
4. **Does rejection track contract size?** Exploratory, because this was seen before the freeze. Within the same task, failing artifacts are larger on L1 (216 tasks against 41) and L4 (180 against 84), with no difference on L2 (144 against 139), and failing the correct-output suite also goes with larger contracts (78 against 32) (measured, `analysis/size_by_check.py`). Pooled rates by size mostly compare tasks, so only within-task results are reported. Once rejections are certified, report whether larger contracts turn out sound and stronger, or overconstrained.
5. **Two-way audit.** Exploratory. A one-way correction can only raise scores. Dominik labels 60 artifacts, 20 each from Clean, Sound and Difference, with class hidden, after calibrating on the paper's 61 reference reviews. This is descriptive and is not a mitigation for the reference problem.

## RQ4 analysis

Sample: the 100 tasks in `results/tasks/rq4_tasks.txt`, a random draw with seed 20261102 from the 654 tasks outside the development set, taken before any Haiku program exists. Tasks were not chosen on any model's results.

Generation: Claude Haiku 5.5 through the paper's StarVerus few-shot adapter, one run per task, with the API key, in two arms. The full arm matches the originals: five candidates, then repair. The bare arm takes one candidate exactly as generated, with no repair. A bare win is the stronger claim, because the handicap can only work against Haiku. A bare loss says nothing until compared with the full arm. Comparators: the release's StarVerus few-shot artifacts for the same 100 tasks from all five original models.

Grading: the frozen grader, unchanged. Haiku artifacts run after the census, so the grader cannot have been tuned on them.

Report per attempt, on all 100 tasks, so failures to verify count against each model: verified, sound in the paper's form, sound in the guarded form, Difference, Undecided. Compare Haiku with each original model by paired bootstrap across tasks. Undecided is never counted either way, so give a low and high bound for each sound rate. Descriptive, with no pass or fail.

Prediction, logged now and scored afterward: Haiku verifies more often than every original model on these tasks (from a biased sample of 20, 20 against 8 to 13). We make no prediction on sound rate, because no earlier data can answer that.

Limits: one model from one vendor, so this does not speak for current models in general. Claude also writes proofs in the grader, and Verus decides each verdict, but Haiku's contracts may suit Claude's proofs better. Sonnet stays in the grader for every model, so all are judged the same way. The reference is still not ground truth, and the authors' point holds: a score here measures comparison with the reference, not whether a contract is correct.

## Procedure

1. Choose one seeded 20% of tasks as the development set. All pilots, costs, stability checks and thresholds use it. Report results with and without those tasks, and with the 30 regrade artifacts removed.
2. Pass gates 1 and 2, then validation.
3. Freeze: tag the commit, record tool and model versions, hash the analysis script, and run it on synthetic data. Tell the authors first, then post to Zenodo.
4. Run the census, then RQ4 generation and grading. No grader changes. A found bug means a logged deviation and a rerun of that tier.

Solo blinding is not enforceable, so the protection is the hash. Agent assistance on the plan, code and analysis is disclosed.

## Threats

- **Prover dependence.** Undecided shrinks with a better prover, and refutation is easier than proof, so shares describe this prover. Mitigation: tier reporting, second proposer.
- **The reference is not ground truth.** Labels say the contracts differ, not which is right.
- **Selection into acceptance.** The census conditions on verification. RQ3 handles this as stated.
- **Conflict of interest.** The author relies on Claude for code and analysis, and Claude proposes proofs. Verus decides. Disclosed.
- **Solo rater with a strong prior.** Audit is exploratory.
- **External validity.** One evaluation, one verifier.

## Budget and schedule

Live status, spend and gates are in [`docs/status.md`](status.md). This section records the method.

The census runs through `analysis/census.py`, stopping at the first verdict: `analysis/witness.py` for counterexamples, then proofs with no model (`analysis/gate2_tier0.py`), then one-shot Haiku and then Sonnet through the Batches API with structured output (`analysis/tier_batch.py`). Model counterexamples are checked by `analysis/gate2_check.py`, which builds them in exec code and verifies them, without compiling and running them. On all 656 development clauses this cost $2.26 (measured), so about $8 for the other 2,387, which is an estimate. On the 100 sampled development clauses it found all 32 proofs and 46 of the 47 refutations that agents had settled, with no conflicts. It uses an API key and the Batches API because that is the pipeline we tested.

Undecided shares in the paper describe this pipeline, which left 18 of 100 development clauses undecided against 21 for agents. Two runs on 200 clauses gave no flips between proved and refuted, and 97.8% of verdicts were identical.

The target is an arXiv paper and a public repository. ICPC 2027 RENE is dropped: the question is not a replication, and reviewers would ask why a recent preprint matters. VerusEval is the case study, because it has a full public release.

## Outline

1. Introduction: rejected, proved and refuted are different results.
2. Background: obligations and premise policy, quoted fairly.
3. Grader and validation on the authors' variants.
4. RQ1: what the rejections are.
5. RQ2: stricter references.
6. RQ3: what changes, and what does not.
7. What holds up in the original.
8. Threats.
9. Recommendations: certify rejections, report undecided as a class, state the premise policy next to any score.

## Related work to read first

[Can LLMs Enable Verification in Mainstream Programming?](https://arxiv.org/abs/2503.14183) already checks generated-implies-reference. Also Verus-SpecGym, Veriact, the ICML 2026 "How Powerful are LLMs in Generating Program Specifications?" paper and the October 2026 SpecGen evaluation paper. The novelty claim is machine-checked resolution of rejected obligations in a published Verus evaluation. A first search found no such paper, which is not proof of absence.
