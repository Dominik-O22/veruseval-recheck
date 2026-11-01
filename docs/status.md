# Project status

This is the single source of truth for what we are doing and why. `docs/paper-plan.md` says how. Last updated 1 November 2026.

## The question

What are the rejected soundness checks in VerusEval really: solver limits, differences outside valid inputs, or real differences?

And do the paper's results carry over to a current model? This was the project's starting point, and it is RQ4 in the plan.

## Rules

1. **Work comes from this page.** A new idea goes under Ideas, not into a run. It moves up only by an explicit decision.
2. **One step at a time.** A gate closes before the next one opens.
3. **Every gate has a pass condition, written before the work starts.**
4. **Only verified numbers count.** A result is verified when Verus decided it and we re-ran it here. A session summary is a report, not a result.
5. **Nothing public until its gate is closed.** That covers README claims, email, Zulip and the paper.
6. **Pilot data stays pilot data.** Everything so far is exploratory, on the 108 development tasks.
7. **Each gate records what it spent.**

## Gates

| # | Gate | Pass condition | Status | Evidence |
|---|---|---|---|---|
| 1 | Rebuild the paper's checks | Regenerated context and status match the released records on L1 and L2 | **Passed** | 151 of 151 clauses here, 117 of 117 in the cloud session |
| 2a | Proofs and counterexamples work | Verdicts reproduce independently on this machine | **Passed** | 182 verdicts on 128 clauses, 0 failed, 0 controls tripped |
| 2b | Cheap pipeline works | No conflicts with verified answers, cost measured | **Passed** | 95 of 103 and 78 of 79 settled, 0 conflicts, about $0.01 per clause |
| 2c | Grader on the authors' known cases | 0 soundness bugs, at least 90% recall on the held-out variants | **Passed** | 719 of 728 in the paper's form, 713 of 728 guarded, 0 proved lemmas refuted, 0 must-clear variants refuted. Re-run here: 7,558 lemmas, 0 changes, no API spend. Cloud session cost $14.79. `results/gate2/witness_verify.json`, `docs/gate2-witness.md` |
| 2d | Guarded proofs have real inputs | Each guarded proof has a confirmed input, or is reported as unconfirmed | **Passed** | 63 of 69 confirmed, 6 reported as unconfirmed, about $0.01. `results/gate2/guard_final.jsonl` |
| 2e | Filter stops rejecting valid proofs | The 7 rejected `axiom` answers are rechecked | **Passed** | 13 answers on 7 clauses rechecked, not 7, 1 clause newly proved, no API spend. 262 other stored answers unchanged. `results/gate2/tier_axiom.jsonl` |
| 2f | Witnesses can use computed values | Changed on dev data only, then frozen before the holdout. With the frozen change: 0 proved lemmas and 0 must-clear variants refuted on dev and holdout, every earlier refutation unchanged, each computed refutation has a clean control, uses only values bound to literals, fits its type and carries its own tag, and the 4 known cases reproduce. The computed proposer must actually run on the holdout, so this tests something | **Passed** | 0 of 3,937 proved lemmas refuted, 1,602 of them attacked with computed values, 0 must-clear variants refuted, all 1,506 earlier refutations unchanged, 3 of 3 and 15 of 15 controls clean, 4 of 4 known cases, no API spend. Logged deviation: the first holdout check replaced 3 plain witnesses, so the order was fixed and the holdout re-run. `results/gate2/computed_verify.json` |
| 3 | Freeze | Plan, grader and analysis script fixed, hashed, dry-run on synthetic data, authors told | **Next** | |
| 4 | Census | All 3,043 clauses run on the 80% of tasks not used in development, plus development tasks reported apart | Blocked by 3 | |
| 5 | Analysis | RQ1 to RQ3 scored as written in the plan | Blocked by 4 | |
| 6 | Draft | Every number traces to a results file, every reference checked by hand | Blocked by 5 | |
| 7 | Outreach | Authors see the draft first, then endorsers | Blocked by 6 | |

## Next action

Gate 3 is running, on Dom's go-ahead of 2 November. Each step has its pass condition here, written before the work. Development tasks only, so no census data is seen before the freeze.

| Step | Work | Pass condition | Status |
|---|---|---|---|
| 3a | One census driver: regenerate, `witness.py`, no-model proofs, Haiku, Sonnet, one verdict table | Runs end to end on all development tasks, regenerated context and status match the release, every verdict comes from Verus | **Passed.** `analysis/census.py`. 656 of 656 clauses matched, 0 lemmas with both verdicts, about $2.26. In the paper's form: 194 proved, 334 refuted, 128 undecided. Pilot data. `results/gate3/verdicts_dev.jsonl` |
| 3b | Plan's Validation 2 to 5 on development tasks | No lemma has both verdicts, no proved lemma refuted, recall reported on hard true and known false cases, flip rate reported from two runs on 200 lemmas | **Passed.** 0 both verdicts, 0 proved refuted. Hard true: 16 of 17 guarded proofs. Known false: 69 of 71 refuted, 0 proved. 0 flips on 200 clauses, 97.8% identical. `results/gate3/validation.json` |
| 3b+ | RQ4 generation script | Runs Haiku on 5 development tasks with the API key through the unmodified StarVerus few-shot path, and the output grades through the census driver | **Passed.** 5 of 5 verified, about $0.10, graded through the free steps. `analysis/rq4_generate.py` |
| 3c | Analysis script | Produces every RQ table from synthetic data with known answers, and each table matches them | **Passed** for RQ1, RQ2, RQ3 items 2 and 3, and RQ4. `analysis/test_census_report.py`. RQ3 items 4 and 5 are exploratory and item 1 uses released labels only, so they sit outside it |
| 3d | Freeze | Plan, grader and analysis hashed and tagged locally, cost estimate updated from 3a, authors' message drafted | **Passed.** Local tag `freeze-1`. `results/gate3/freeze.sha256`. Census about $8, RQ4 about $3 |
| 3e | Tell the authors | Dom approves the message and it is sent | Waits for Dom |

Spending cap for gate 3: $10 of the API key.

Before the freeze:

- Run the plan's Validation 2 and 3 (hard true cases, known false cases). No gate has covered them yet. Validation 5 (stability) still needs a run on the proof tiers. `witness.py` already shows 0 changes between two machines.
- Choose the free tier. Recommended: `witness.py` in place of `tier_free.py`, because on the 100 development clauses in the paper's form it takes the pipeline from 26 undecided to 21, the same as agents, with 0 conflicts and no API spend. Computed values take it to 19 unaided, and 17 with hand witnesses.
- Treat the 98.76% as an upper estimate. The proposer reads the same I/O suites the authors used to confirm these variants. On the natural development lemmas it found 48 of the 72 refutations already verified here.

## Budget

| Source | Available | Spent | Use |
|---|---|---|---|
| API key | $100 | about $5 | Census (about $8 for the other 2,387 clauses, scaled from the 656 development clauses), then RQ4 |
| Cloud credit, expires 5 Nov 08:59 | $214 left | $36 | Gate 2c only, unless a gate needs agents |

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2 Nov | Add RQ4: Haiku 5.5 on 100 random tasks through the frozen grader, written into the plan before the freeze. Haiku only | It is Dom's original point, and the census gives it a fair baseline. Haiku is the same class as the original models |
| 1 Nov | First paper certifies rejected checks, and the workflow study is a separate note | It tests a different claim and needs its own design |
| 1 Nov | No collaboration pitch yet | Bring results first |
| 1 Nov | Do not race the credit deadline | A wrong run costs more than lost credit |
| 1 Nov | Census instead of a 600-check sample, if the pipeline holds at gate 3 | Measured cost fits the key |
| 1 Nov | No general retry step | $0.56 bought 3 proofs in 40 |
| 1 Nov | No "Undefined only" class. Computed refutations get their own group, never counted as real differences | Second opinion showed the class would state false things, and a read of nothing can be noise or a real hole (`VD0138`) |
| 1 Nov | Gate work stays on local branch `gate2-local`, nothing pushed | Pushing would publish pilot numbers |

## Open questions for others

- **Authors:** where are the original task requirements for tasks other than MBPP? Needed for RQ2. Their answer does not block gates 2 to 4.
- **Endorser:** none yet. Blocks arXiv, not the work.

## Ideas, not scheduled

Each needs a decision before it runs.

- Sort computed refutations by evidence: look for a real implementation that passes the generated contract and fails the reference. One hand test on `VD0138`: wiping the list passes the generated contract and fails the reference.
- Blind review, confirmatory run. Pilot: 18 of 22 real differences caught, 7 of 60 clear units alarmed.
- Sample of about 100 "promises more" checks on the largest contracts, for the longer-contracts question.
- Workflow note: agent against pipeline.
- Telling the authors about the lynette copies, or about pilot results. Wait for gate 5.
