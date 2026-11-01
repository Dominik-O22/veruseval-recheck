# Project status

This is the single source of truth for what we are doing and why. `docs/paper-plan.md` says how. Last updated 1 November 2026.

## The question

What are the rejected soundness checks in VerusEval really: solver limits, differences outside valid inputs, or real differences?

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
| 2c | Grader on the authors' known cases | 0 soundness bugs, at least 90% recall on the held-out variants | **Passed** | 719 of 728 in the paper's form, 713 of 728 guarded, 0 proved lemmas refuted, 0 must-clear variants refuted. Re-run here: 7,558 lemmas, 0 changes, no API spend. Cloud cost not reported. `results/gate2/witness_verify.json`, `docs/gate2-witness.md` |
| 2d | Guarded proofs have real inputs | Each guarded proof has a confirmed input, or is reported as unconfirmed | **Passed** | 63 of 69 confirmed, 6 reported as unconfirmed, about $0.01. `results/gate2/guard_final.jsonl` |
| 2e | Filter stops rejecting valid proofs | The 7 rejected `axiom` answers are rechecked | **Passed** | 13 answers on 7 clauses rechecked, not 7, 1 clause newly proved, no API spend. 262 other stored answers unchanged. `results/gate2/tier_axiom.jsonl` |
| 3 | Freeze | Plan, grader and analysis script fixed, hashed, dry-run on synthetic data, authors told | **Next** | |
| 4 | Census | All 3,043 clauses run on the 80% of tasks not used in development, plus development tasks reported apart | Blocked by 3 | |
| 5 | Analysis | RQ1 to RQ3 scored as written in the plan | Blocked by 4 | |
| 6 | Draft | Every number traces to a results file, every reference checked by hand | Blocked by 5 | |
| 7 | Outreach | Authors see the draft first, then endorsers | Blocked by 6 | |

## Next action

Start gate 3 when Dom gives the go-ahead. It ends with telling the authors, so it needs his go-ahead on that message.

Before the freeze:

- Run the plan's Validation 2 and 3 (hard true cases, known false cases). No gate has covered them yet. Validation 5 (stability) still needs a run on the proof tiers. `witness.py` already shows 0 changes between two machines.
- Choose the free tier. Recommended: `witness.py` in place of `tier_free.py`, because on the 100 development clauses in the paper's form it takes the pipeline from 26 undecided to 21, the same as agents, with 0 conflicts and no API spend.
- Treat the 98.76% as an upper estimate. The proposer reads the same I/O suites the authors used to confirm these variants. On the natural development lemmas it found 48 of the 72 refutations already verified here.

## Budget

| Source | Available | Spent | Use |
|---|---|---|---|
| API key | $100 | $1.43 | Census (about $19 to $32, estimated from 128 clauses) |
| Cloud credit, expires 5 Nov 08:59 | $219 left | $31 | Gate 2c only, unless a gate needs agents |

## Decisions

| Date | Decision | Why |
|---|---|---|
| 1 Nov | First paper certifies rejected checks, and the workflow study is a separate note | It tests a different claim and needs its own design |
| 1 Nov | No collaboration pitch yet | Bring results first |
| 1 Nov | Do not race the credit deadline | A wrong run costs more than lost credit |
| 1 Nov | Census instead of a 600-check sample, if the pipeline holds at gate 3 | Measured cost fits the key |
| 1 Nov | No general retry step | $0.56 bought 3 proofs in 40 |
| 1 Nov | Gate work stays on local branch `gate2-local`, nothing pushed | Pushing would publish pilot numbers |

## Open questions for others

- **Authors:** where are the original task requirements for tasks other than MBPP? Needed for RQ2. Their answer does not block gates 2 to 4.
- **Endorser:** none yet. Blocks arXiv, not the work.

## Ideas, not scheduled

Each needs a decision before it runs.

- Blind review, confirmatory run. Pilot: 18 of 22 real differences caught, 7 of 60 clear units alarmed.
- Sample of about 100 "promises more" checks on the largest contracts, for the longer-contracts question.
- Current models on 100 random tasks, for the weak-models question.
- Workflow note: agent against pipeline.
- Telling the authors about the lynette copies, or about pilot results. Wait for gate 5.
