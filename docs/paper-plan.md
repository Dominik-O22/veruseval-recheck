# Paper plan: certifying rejected comparisons in VerusEval

Status: revision 3, 1 November 2026, after two rounds of adversarial review. Not frozen. The two feasibility gates below must pass first. Numbers marked measured come from the VerusEval release or this repo, and numbers marked guess are planning assumptions.

## The paper in one paragraph

VerusEval (arXiv 2610.26464) compares LLM-written Verus contracts with references. Its authors say plainly that "A rejected obligation is a failed proof attempt, not a confirmed semantic difference." That leaves thousands of comparisons undecided. This paper decides as many as it can. For each rejected soundness lemma on the 2,166 accepted artifacts that have one, it produces a Verus-checked proof or a concrete counterexample, under the paper's unconditional comparison and under a guarded one that assumes both preconditions. The result is a certified account of what those rejections are, plus a reusable grader.

Working title: *Certifying Rejected Contract Comparisons in VerusEval*. The final title should state the measured result.

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

The 2,370 rejected obligations are a gap the paper describes and leaves open. It is not an error we are correcting. Email the corresponding author, Dugang Liu, as well as Ding Wang.

## Research questions

**RQ1, what the rejections are.** For each rejected L1 and L2 lemma, what does certification find under each comparison form?

**RQ2, stricter references.** On how many tasks outside the 148 numeric-list tasks does a sound, same-code contract show that the reference's precondition rejects inputs the code handles?

**RQ3, what changes.** Descriptive only. How do I/O screening and the configuration comparisons look once rejections are certified?

## Out of scope

The workflow experiment becomes a separate note. VeruSteer's result is a replay-only selector gain, and its paper says that design "does not describe an end-to-end benchmark". Requirements for that note, from review: one agent harness for both models, no shared host mount, a calibration arm on the released pipeline, pinned spec fns, an AST-based bypass check, zero acceptance on frozen-unfixable trees as a negative control, runs keyed by `tree_id`, no token cap, arms interleaved by tree, and the 30 pilot trees excluded.

Also out: `tasks_fair20.csv`, the 12 Haiku tasks, the blind-review finding, the frontend failure statistics, and any model ranking. They stay in the repo as exploratory. L3 and L4 stay out of the census, which means this paper cannot retest the 63.2% equivalence figure, and it says so.

## Population

| Item | Size | Source |
|---|---|---|
| Accepted artifacts | 7,081 | measured |
| Rejected L1, L2 obligations | 609, 1,761 | measured |
| Rejected clause lemmas, L1, L2 | 723, 2,320 (3,043 total) | reviewer measured, confirm at gate 1 |
| Accepted artifacts with a rejected L1 or L2 | 2,166 on 541 tasks | measured |
| All artifacts with a rejected L1 or L2 | 4,365 | measured |
| Rejected L2 valid under the older guarded form | 537 of 1,761 | measured |
| Rejected L2 with no real precondition on either side | 369 | reviewer measured |
| Tasks with a rejected L3 outside the numeric list | 182 | reviewer measured |

The unit is the clause lemma, because that is what the labels record. An obligation is proved when every rejected clause lemma is proved, and refuted when any is.

The census covers accepted artifacts only. The other 2,199 artifacts with rejections failed verification, and regrading a contract the verifier rejected would answer a different question. That choice affects RQ3, which accounts for it.

## The grader

One rule: only a positive Verus result produces a verdict. A timeout or failed attempt never does.

**Regeneration.** The stored `formal_recheck` harnesses cover 214 artifacts (measured), and those are `proof_failed` artifacts, not this population (reviewer measured). So we regenerate through the release's `metrics/_clause_implication.py` and require a match on the stored `obligation_sha256` before using a lemma. This is gate 1.

**Two forms.** Unconditional is the paper's form. Guarded adds both preconditions to the antecedent. A guarded refutation is also an unconditional refutation with the same witness, and an unconditional proof is also a guarded proof, so results propagate and each pair needs at most two searches. Where neither side has a real precondition, the two forms are one formula and get one search.

**Proved.** Verus accepts a proof of the unchanged lemma, with no `assume`, `admit`, `external_body` or new `#[verifier]` attribute.

**Refuted.** A proposer returns literal values only. A fixed template, with no loops, branches or calls, binds them and asserts the antecedent and the negated consequent, with `reveal_with_fuel` where needed, following the release's concrete-value engine in `contract_eval.py`, which proves `assert(Q)` or `assert(!Q)`. The same file with `assert(false)` is also run. If that verifies, the context is inconsistent and the verdict is void. Its failure proves nothing and is not used as evidence, so this check can only remove a verdict.

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
2. **Hard true cases.** The variant bases are easy, because they were selected as already equivalent. Add the 7 model-proved rows from `regrade-30`, the proofs in `proofs/`, and any others with a checked proof.
3. **Known false cases.** Natural obligations with a failing correct or wrong-output case, up to 419, after reading each case's reason.
4. **Both engines.** On validation sets only, run prover and refuter on every lemma. Any lemma with both verdicts is a soundness bug and stops the run.
5. **Stability.** Run the frozen grader twice on 200 development lemmas and report the flip rate.

Gates, fixed now: zero soundness bugs, at least 90% recall on refutation and on proof for the variants. Recall on the hard sets is reported, because those define the real instrument error. RQ1 is a census, so it has no sampling interval, but instrument error is real and is reported next to every share.

## RQ1 analysis

Report the grid by lemma, form, configuration and type class. Report the search tier that produced each verdict, because shares depend on the prover. Undecided is never counted either way.

Predictions, logged now and scored afterward, with no pass or fail attached. On the 1,909 obligations with no failing I/O case: proved in some form 40%, certified false 35%, Undecided 25% (guess from the pilot's 9 proved, 16 claimed and 1 unresolved of 26, all guarded). Premise-only share of rejected L2: above 20% (guess, because 537 is an upper hint, not a count).

A second, non-Claude proposer runs on a random 200 Undecided lemmas, to show how much the result depends on the prover. In this paper the subjects are DeepSeek, Qwen, GPT-4o and Llama, so Claude is an instrument here and not a subject.

## RQ2 analysis

Unit: task. A task counts when at least one accepted artifact meets all of these: same executable code as the input under the fixed lynette build from microsoft/verus-proof-synthesis#53, all L1 and L2 valid or proved, and an L3 witness the reference rejects. One such artifact is enough, because it shows the code is safe and the contract is sound on that input.

Reviewer counts outside the numeric list: 159 same-code tasks, 109 with L2 valid, 103 with L1 and L2 valid. So the result is close to known, and RQ2 is an estimate, not a test. 0 of 762 inputs contain `requires` or `ensures` (reviewer measured), and 10 have a non-empty `main` (measured), so nearly all inputs give no signal. The 10 are tagged.

Comparator: 148 numeric-list tasks. The 36 candidate reference defects are a different construct and are tracked separately. Hand-label a random 60 counted tasks to estimate precision.

## RQ3 analysis

Descriptive, in a fixed order, with no claim that a finding reverses.

1. **Definition-only row first.** With released labels and no proofs, 736, 1,337 or 1,867 artifacts move depending on how I/O is treated (measured). These are redefinitions, reported as such, so they are never mistaken for grader results.
2. **I/O screening.** Among 4,749 I/O-passing artifacts, 78.7% are proved sound on the released labels (measured). Of the 1,012 with a rejected L1 or L2, report how many become proved and how many become certified false. A certified difference on an I/O-passer supports the paper's concern, and we say so. Reporting 78.7% is not a retest of 63.2%, which needs L3 and L4.
3. **Configuration comparisons.** Exploratory. Census coverage correlates with acceptance at 0.907 across configurations (reviewer measured), so relabeling alone tends to raise the acceptance link. We therefore recompute on accepted artifacts only, call that a new estimand, and publish a random-relabel negative control. On the 13 of 14 matched pairs with a clear acceptance gap, report how many are concordant for each metric, original versus certified, with paired bootstrap deltas.
4. **Two-way audit.** Exploratory. A one-way correction can only raise scores. Dominik labels 60 artifacts, 20 each from Clean, Sound and Difference, with class hidden, after calibrating on the paper's 61 reference reviews. This is descriptive and is not a mitigation for the reference problem.

## Procedure

1. Choose one seeded 20% of tasks as the development set. All pilots, costs, stability checks and thresholds use it. Report results with and without those tasks, and with the 30 regrade artifacts removed.
2. Pass gates 1 and 2, then validation.
3. Freeze: tag the commit, record tool and model versions, hash the analysis script, and run it on synthetic data. Tell the authors first, then post to Zenodo.
4. Run. No grader changes. A found bug means a logged deviation and a rerun of that tier.

Solo blinding is not enforceable, so the protection is the hash. Agent assistance on the plan, code and analysis is disclosed.

## Threats

- **Prover dependence.** Undecided shrinks with a better prover, and refutation is easier than proof, so shares describe this prover. Mitigation: tier reporting, second proposer.
- **The reference is not ground truth.** Labels say the contracts differ, not which is right.
- **Selection into acceptance.** The census conditions on verification. RQ3 handles this as stated.
- **Conflict of interest.** The author relies on Claude for code and analysis, and Claude proposes proofs. Verus decides. Disclosed.
- **Solo rater with a strong prior.** Audit is exploratory.
- **External validity.** One evaluation, one verifier.

## Budget

Stop at the first verdict on the census. The pilot cost about $0.05 per obligation (measured, $1.30 for 26), and hard ones will cost more. A range of $150 to $300 is plausible, and running every ladder in full would approach $1,400 (reviewer inferred). The cap is $300. Measure on the development set before the freeze. Use an API key: Anthropic's terms say Agent SDK developers "should use API key authentication", and that subscription limits "assume ordinary, individual usage". The second proposer needs a pinned paid endpoint. If the cost exceeds the budget, use a seeded random half of tasks and report it.

## Timeline

| By | Gate | If it fails |
|---|---|---|
| 3 Nov | Public README correction pushed, authors told about the premise policy | No outreach until done |
| 8 Nov | Gate 1: regenerate lemmas with matching hashes | Narrow to what regenerates, or stop |
| 10 Nov | Gate 2: literal-witness template works on L1 and L2 for each type class | Report type classes as Undecided |
| 14 Nov | Validation passes, cost measured | Fix, and move every date below |
| 15 Nov | Freeze, Zenodo | No confirmatory run before this |
| 24 Nov | Census complete | Seeded half of tasks |
| 29 Nov | Analysis | Report what holds |
| 3 Dec | Draft to authors and potential endorsers | No posting without this |
| 10 Dec | Responses handled | Note non-response |
| 11 and 18 Dec | Optional ICPC 2027 RENE | arXiv only |

A slip of one to two weeks is likely (guess), and missing ICPC does no harm, because arXiv is the primary target. Endorsement runs in parallel.

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
