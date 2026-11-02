# veruseval-recheck

A re-check of VerusEval (arXiv 2610.26464) and VeruSteer (arXiv 2610.29755) from Ding Wang's group, now turning into a short paper on what a VerusEval score measures. Certifying rejected contract comparisons is one part of it.

Start with `docs/status.md`. It is the single source of truth for what we are doing, the gates, spending and decisions. `docs/paper-plan.md` says how. Update `docs/status.md` whenever a gate moves.

## Working rules

- Work comes from `docs/status.md`. A new idea goes under Ideas until Dom decides to run it. Dom has twice had to pull this project back from being reactive, so do not start side experiments.
- One gate at a time, with its pass condition written before the work starts.
- A verdict counts only if Verus produced a positive result. A timeout or failed attempt is never a verdict, and a model's claim is never a verdict.
- A number counts only after it is re-run on this machine. A session's summary is a report, not a result.
- Everything so far is exploratory. Use only the tasks in `results/tasks/dev_tasks.txt`, plus cases the status page names, until the freeze.
- Nothing goes public until its gate closes: README claims, email, Zulip, GitHub comments, the paper. Pushing, sending and commenting need Dom's go-ahead each time.
- Before any public claim, check it against the paper text and the data. Read the paper before criticizing the code.

## Facts that are easy to get wrong

- **Verified** means Verus accepted the code against the model's own contract. The rejected checks are on contracts that did verify. They are not syntax failures.
- **Rejected is not false.** Each comparison gets one Verus attempt with no proof guidance. The paper says this itself: "A rejected obligation is a failed proof attempt, not a confirmed semantic difference."
- **Guarded versus unconditional.** The released L2 and L4 labels are unconditional, with `postcondition_premise_policy: no_preconditions`. `semantic_strength.py`, and so `scripts/adjudicate.py` and `scripts/reevaluate.py`, use the guarded form with both preconditions added. A guarded proof does not discharge a released L2. Never call one "evaluator wrong". This is the mistake the authors caught.
- **Three tests, three names.** Exact-match test: the 42.3% headline, where stronger contracts fail. No-preconditions test: the paper's L1 and L2. Valid-inputs test: the same with both preconditions assumed. Do not say "strict test".
- **The released labels come from the per-clause path** in `metrics_rebuild/share/smt.py`, not `semantic_strength.py`. Use `analysis/gate1_regenerate.py` and `analysis/gate2_regenerate.py`.
- **Two of the three checks rest on the reference.** The paper says the I/O suites "rest on the same reference as specification correctness", so they are not independent of the contract comparison. Triviality looks at the generated contract alone.
- **Models see only code.** The 762 inputs have no task description, and the only comment is `// verus!`. Public text exists for 435 tasks, used only in RQ5.
- **An unresolved I/O check is incomplete, not flagged.** The paper has 3,790 flagged artifacts and 296 unflagged but incomplete.
- **Stored hashes cannot be matched.** Digests depend on absolute paths and the Verus binary, and wrapper names carry path-dependent hashes. Gate 1 compares `obligation_context` and status. Spliced proofs must map `__sqm_gen_*` names, as `analysis/gate2_verify.py` does.
- **A computed refutation is not a real difference.** It defines a value from a read Verus leaves unspecified, so it has no single concrete input and cannot be run. Report these as their own group. It refutes the lemma in Verus's logic, which may be noise or a real hole, as with `VD0138`.
- **Do not reuse `capture_checks` across threads.** It patches module globals.
- Failing checks correlate with contract size mostly because hard tasks need bigger contracts. Compare within a task, as `analysis/size_by_check.py` does.

## Where things are

Harnesses, references and the release are not in this repo and must not be committed, because it does not redistribute them.

- Release: `~/.t3/scratch/2026-10-26-how-costly-would-it-be-4c519b9c/veruseval-release`
- VeruSteer artifact: `.../dl-verusteer-repo/VeruSteer`
- Regenerated harnesses and tier outputs: `.../run-artifacts/gate2-run`
- Paper text: `.../run-artifacts/paper-text`
- Gate 2 scripts and proofs: branch `gate2-proofs` on GitHub, commit `6a9b970`. Merged only on local branch `gate2-local`, which holds the scripts, not on `main`. `analysis/tier_free.py`, `tier_batch.py` and `guard_check.py` import its `gate2_check.py`.
- Counterexample engine: `analysis/witness.py`, branch `gate2-witness` on GitHub, commit `18c99cb`, also merged only on `gate2-local`. Frozen at `5bc30a5` after gate 2f, sha256 `a568da38...`. See `results/gate3/freeze2.sha256`, and treat any change to those files as a logged deviation. It runs in the container with `python3.11 -I` from the release root. `analysis/witness_jobs.py` rebuilds its job files from the results tables, and `analysis/witness_report.py` is its report, renamed because `gate2_report.py` already existed.

## Running things

- Verus 0.2025.09.25.04e8687 is in podman image `veruseval:haiku`. Run from the release root with the release mounted at `/workspace`. Use `python -I` for anything reading release data.
- Census model calls use the API key through the Batches API, because that is the pipeline we tested and it stays reproducible. This is a method choice. Anthropic's API key requirement is aimed at developers building products or services, so personal use of a plan is a separate question, and any switch would need re-validating. `analysis/tier_batch.py` runs on the host with the `anthropic` package and `ANTHROPIC_API_KEY`, for example from a venv.
- Cloud sessions start only from a real terminal, with `CCR_FORCE_BUNDLE=1 claude --cloud "$(cat brief.txt)"`, so Dom has to start them. They are good for agent work and spend the cloud credit. Their files vanish when the VM is reclaimed, so results must be pushed or pasted.

## Writing

Use plain language. Every claim carries its evidence. Say what held up in the original papers as well as what did not.
