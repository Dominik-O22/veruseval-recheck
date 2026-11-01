# Gate 2: the literal-witness counterexample engine

Status: built and validated on 1 November 2026, branch `gate2-witness`. The engine code was frozen at
commit `918983c` (`analysis/witness.py`, sha256 `7776d1f8a9520b26634d6580a350e703b54cda5c93aa1130a70601805bb0e0e5`)
before the holdout variants were run, and it was not changed afterwards. Every number below comes from
that frozen code unless it is marked as coming from an earlier development run.

## What the engine does

`analysis/witness.py` implements the plan's "Refuted" design.

1. **Obligation.** It runs the release's own per-clause path (`smt.clause_implication_details_for_context`
   for L1 and unconditional L2, and `lemma_implication_check` with both preconditions added for guarded L2).
   It records the exact harness that path builds: the reference file, copied support items, the per-clause
   wrapper spec fns and the lemma. Nothing in the release is patched. It only observes `_make_lemma`,
   `build_clause_wrapper` and `subprocess.run`.
2. **Proposer.** A proposer returns literal values only, named as in the source signature (`inputs`,
   `post` for `&mut` post-states, `output`). Two proposers exist. `io_and_boundary` is code: the task's frozen
   I/O cases from `data/io`, one-step perturbations of them, type defaults and length-only extremes. `model` is
   hand-written literals in a JSONL file (this session wrote them, with no script calling a model).
3. **Template.** One fixed `proof fn` with the lemma's own parameter list, `requires` pinning each parameter to
   its literal (`x == 5i32`, `a@ == seq![1i32, 2i32]` plus the element facts, `s@ == seq!['a']`,
   `o is Some && o->Some_0 == ...`, field-wise for tuples and structs), `reveal_with_fuel` for recursive spec
   fns reached by the clauses (as `contract_eval._fuel_reveal_lines` does), `assert(antecedent)` for each
   antecedent call and `assert(!(consequent))`. There are no loops, branches or calls. Because the parameters are
   the lemma's parameters and the asserted calls are the lemma's own wrapper calls, a verified witness shows that
   the lemma's requires hold and its ensures fail at the pinned values.
4. **Verdict.** Candidates are screened in one batch file (24 per lemma, `--rlimit 2`). A hit is then confirmed
   in a standalone file at the release's `--rlimit 10`. Only `verified >= 1`, `errors == 0`, no error and no
   timeout counts. The same file with the body replaced by `assert(false)` is the control. It must reach
   verification and fail with "assertion failed", otherwise the verdict is void. Timeouts, compile failures and
   failed runs never yield a verdict.
5. **Realization.** For each confirmed witness the values are built by exec code (`vec![..]`,
   `String::from_str`, `as_slice()`, struct and tuple literals) in an exec fn that re-proves the pins and asserts
   the same formulas. It is verified with Verus, compiled with `--compile` and run. A witness that needs a value no
   program can allocate, such as a `Vec<u64>` of length `usize::MAX`, is reported as **unrepresentable**, its
   own class.
6. **Forms.** L2 is searched guarded first. A guarded witness is tried first on the unconditional lemma, as the
   plan's propagation rule allows. It is still confirmed there by Verus, not inferred.

The Python evaluator from `contract_eval.eval_contract_expr` only orders candidates. It has a 3 s budget per
lemma and skips clauses with more than one quantifier binder. It never produces or removes a verdict.

### Known limits of the template

- f32 and f64: only equality is expressible. At this Verus version `<` on `f32` in spec does not compile
  (`no method named spec_lt found for type f32`), so ordered float clauses cannot appear in a working
  harness. NaN and infinities are not bound as literals.
- `usize` and `isize` literals beyond the 32-bit range are pinned as `(x as int) == N`, because Verus rejects the
  suffixed literal while the word size is open. Such a witness speaks about 64-bit targets. Records carry
  `assumes_64bit_usize`. The realization file states `global size_of usize == 8`, which holds on the x86_64 machine
  that compiles and runs it.
- A struct field of type `Vec` compared with `==` against a parameter (`result.coef == coefficients`) cannot be
  established from view pins, so such lemmas stay Undecided (1 seen on dev, `VT0457`).
- Generic type parameters, data-carrying enums, `Map` and types the release's `type_defs` cannot parse are
  `unsupported_type`, never a verdict (45 dev census lemmas on `VT0269`, `VD0197`, `VT0048`).
- Spec fns that are unspecified outside a `when` domain, such as `gcd` on non-positive inputs, cannot be separated
  by literal evaluation (`VD0431`, read by hand).

## Results

All tables are in [`results/gate2`](../results/gate2), keyed by sample ID, and `tables.md` holds them as
markdown. The release's references are not in this repository. Witness and control files embed the reference
harness, so they were kept on the VM and are not committed.

### Soundness

- **0 soundness bugs.** No lemma that Verus proves (release status `valid`, or my guarded lemma proved by
  Verus) was refuted. That is 0 of 4,410 proved lemmas, each searched with up to 24 candidates
  (`both_verdicts.csv` is empty). No variant expected to clear was refuted: 0 of 1,077 must-clear rows, 97 dev and
  980 holdout, in each form (`variant_unexpected_refutations.csv` is empty).
- **Controls.** Every one of the 1,079 holdout, 121 dev variant and 306 dev census refutations had a clean control:
  `assert(false)` reached verification and failed. No control verified, so no verdict was voided. In development
  runs 3 hits were dropped as "control inconclusive". That was an engine bug: stderr was truncated before the check.
  It was fixed before the freeze. It removed verdicts, never added them.
- **The impossible grid cell is empty.** On the dev census no L2 lemma is refuted guarded and proved unconditional.

### Validation on `data/evidence/contract_variants` (plan, Validation 1)

These are the 943 retained variants (`data/evidence/paper_results/RQ3/results/variants/retained_variants.csv`):
89 on 21 dev tasks were used for development, and 854 on the other 183 tasks were run once on the frozen code with
the mechanical proposer only. A variant counts as refuted when any of its clause lemmas in the expected direction has
a verdict.

| Split | Forms | Must refute | Refuted | Recall | Must-clear rows | Unexpected refutations |
|---|---|---|---|---|---|---|
| dev | L1 and unconditional L2 (paper form) | 81 | 81 | 100% | 97 | 0 |
| dev | L1 and guarded L2 | 81 | 81 | 100% | 97 | 0 |
| holdout | L1 and unconditional L2 (paper form) | 728 | 719 | 98.76% | 980 | 0 |
| holdout | L1 and guarded L2 | 728 | 713 | 97.94% | 980 | 0 |

Holdout recall by operator, each in its own direction:

| Operator | Direction | Must refute | Refuted | Missed | Recall |
|---|---|---|---|---|---|
| PRE_ADD | L1 | 144 | 144 | 0 | 100% |
| PRE_REFINE | L1 | 209 | 209 | 0 | 100% |
| POST_REMOVE | L2 unconditional | 202 | 194 | 8 | 96.04% |
| POST_RELAX | L2 unconditional | 173 | 172 | 1 | 99.42% |
| POST_REMOVE | L2 guarded | 202 | 192 | 10 | 95.05% |
| POST_RELAX | L2 guarded | 173 | 168 | 5 | 97.11% |

Must clear on the holdout: PRE_REMOVE 33 of 33, PRE_RELAX 26 of 26, POST_ADD 64 of 64 and POST_REFINE 3 of 3
cleared in every direction and form.

**The gate passes:** 0 soundness bugs, and 98.76% (719 of 728) recall on must-refute variants in the paper's form,
97.94% (713 of 728) with guarded L2.

**What failed.** All 9 paper-form misses and all 15 guarded misses are on L2. In every one the 24 screened
candidates compiled and none verified, so the miss is the mechanical proposer's budget. None was a compile
failure, a timeout or an unsupported type. The misses are concentrated on tasks with tuple returns
(`VD0797`, `MBPP-verified_task_41`, `VJ0077`), string outputs (`VA0575`, `VA0625`) and `MBPP-verified_task_24`.

**Caveat on what this recall measures.** The release confirmed these variants partly with witnesses drawn from the
same frozen I/O suites (`data/io`) that the mechanical proposer reads (`difference_witness.source` such as
`frozen:neg_001_2`). Recall here is therefore an upper estimate for natural obligations, where no difference was
designed in. On the dev census, 306 of 967 searched rejected lemmas were refuted, and many of the rest are true,
as the reading below shows.

### Positive control: `MBPP-verified_task_73` (`StarVerus|deepseek-chat|few-shot`)

| Form | Release or guarded status | Proposer | Result | Witness |
|---|---|---|---|---|
| unconditional L2 | rejected | model (hand literal) | refuted, control clean, realized | `n = 0, result = true` |
| guarded L2 | proved by Verus | model plus 22 mechanical | not refuted | none |
| unconditional L2 | rejected | mechanical only | refuted, control clean, realized | `n = 1, result = true` |
| guarded L2 | proved by Verus | mechanical only | not refuted | none |

This is the expected Premise-only shape. The authors' witness refutes the paper's form, and nothing refutes the
guarded form, which Verus proves.

### Type classes

"Works" means Verus verified a witness of that class with a clean control. Lemmas can be in several classes.
Rows count clause lemmas. Census rows are rejected lemmas on dev tasks, mechanical proposer only.

| Class | Fixtures (refuted of must-refute) | Dev census: searched / refuted | Holdout variants: refuted lemmas | Hand witnesses (dev census) | Works? |
|---|---|---|---|---|---|
| integers | yes | 791 / 238 | 892 | | yes |
| Vec | yes | 716 / 230 | 969 | | yes |
| slices | | 143 / 33 | 90 | | yes |
| arrays | 1 of 1 | 7 / 1 | | | yes |
| char | 1 of 1 | 113 / 14 | 123 | | yes |
| strings (`String`, `&str`, `Vec<String>`) | 3 of 3 (2 needed hand literals) | no dev obligation has these types | 6 | | yes, `String` only with hand literals so far |
| tuples | 1 of 1 | 13 / 3 | 1 | | yes |
| Option | 1 of 1 | 67 / 4 | | 2 of 2 refuted | yes |
| structs | 1 of 1 (hand literal) | 40 / 3 | | 3 of 4 refuted | yes, except a `Vec` field compared with `==` (`VT0457`, Undecided) |
| unit enums | 1 of 1 | | | | yes. Data-carrying enums are unsupported |
| f32, f64 | 2 of 2 (f64 hand literal) | 120 / 68 | | | yes for equality. Ordered float clauses cannot be stated at this Verus version |
| int, nat | | 14 / 2 | 79 | 3 of 3 refuted (`cube_elements`) | yes. Ghost types, so realization does not apply |
| recursive spec fns | | 121 / 4 | 10 | | yes, with `reveal_with_fuel` |
| `old()` and `&mut` | | 31 / 11 | 191 | | yes |
| generic, `Map`, unparsed types | | 45 unsupported | | | no, reported as `unsupported_type` |

The low census rates for recursion, Option and structs are mostly not engine failures. I read 4 randomly chosen
undecided recursive-spec-fn lemmas, and all 4 are true: two equivalent recursive definitions, a Fibonacci
monotonicity fact, and a digit-factorial table that matches its recursive definition. They are proof cases. Of 6
undecided Option, struct and int/nat lemmas, 5 were refutable but needed coordinated values in several parameters,
which one-step perturbation does not reach. My hand-written literals refuted them through the frozen engine, with
clean controls (`model_tier_census_dev.csv`, 7 of 8 lemmas). The sixth (`VD0431`, `gcd`) is not separable by literals.

### Realizability

| Run | Refuted | Built, verified, compiled and ran | Unrepresentable | Not run |
|---|---|---|---|---|
| holdout variants | 1,079 | 1,005 | 0 | 74 (71 ghost `int`/`nat`, 3 exec version failed an assertion) |
| dev census | 306 | 294 | 12 | 0 |
| fixtures | 19 | 18 | 1 (by design) | 0 |

The 12 unrepresentable dev census witnesses are all L1 refutations that need a `Vec` of length `usize::MAX`
(tasks `DAFNY2VERUS-COLLECTION_54`, `_205`, `MBPP-verified_task_46`, `_53`, `VerusBench_MBPP_task_id_249`, `_251`,
`VA0291`, `VT0055`). That is the "stricter only on inputs that cannot exist" shape from the 30-artifact pilot, now
machine-checked. The engine tries representable hits first, so for these no representable witness was among the
hits. That is not a proof that none exists.

### Engine defects found after the freeze (not fixed, reported)

- 184 of 5,301 holdout screening batches failed to compile with "integer literal out of range USize". The
  `(x as int)` rendering covers scalar `usize` pins but not `usize` elements inside `seq![..]`. Bisection isolated
  the bad candidates and no lemma lost all its candidates, but some candidates were lost, so recall may be
  slightly low. It cannot cause a wrong verdict.
- 3 exec realizations failed an assertion that the proof witness had verified. They are reported as "not run", not
  as realized.
- The release's Python evaluator, used only for ranking, prints `SyntaxWarning: invalid decimal literal` on typed
  literals such as `5usize`. Those candidates rank as unknown.

### Wall time per check

Each worker runs Verus with `--num-threads 1`, and 4 workers ran in parallel on 4 cores. "Search" is the
witness search for one clause lemma, from screening through control and realization. The release's own per-clause
check, which builds the harness and gives the prover status, is separate and is shared by the clauses of one
direction and form.

| Run | Outcome | Checks | Mean | Median | p90 | Max |
|---|---|---|---|---|---|---|
| holdout variants | refuted | 1,079 | 2.63 s | 2.52 s | 3.24 s | 11.7 s |
| holdout variants | undecided | 3,961 | 1.54 s | 1.30 s | 1.97 s | 174 s |
| dev census | refuted | 306 | 2.52 s | 2.42 s | 3.14 s | 4.40 s |
| dev census | undecided | 661 | 1.24 s | 1.09 s | 1.79 s | 5.57 s |

All-in, including the release's checks and every clause: the holdout run took 14,224 worker-seconds for 5,040
clause lemmas (2.8 s each, 3.95 hours of worker time, 60 minutes of wall time on 4 workers). The dev census took
3,585 worker-seconds for 967 searched rejected lemmas (3.7 s each, about 15 minutes of wall time). Verus
subprocesses were 90.2% of worker time on the holdout (12,834 s of 14,224 s) and 93.2% on the dev census
(3,342 s of 3,585 s). The rest is Python.

### Model versus Verus in this session

Measured: the session ran from 17:41 to about 20:15 UTC, roughly 154 minutes. Verus jobs were running for about
127 of those minutes, the frozen holdout run alone for 60. Summed over workers, Verus subprocesses used about 24,000
seconds, 6.7 process-hours across 4 cores. Of those, 17,800 s were the frozen runs: 12,834 s holdout, 3,342 s dev
census, 1,416 s dev variants and 175 s fixtures, controls and hand witnesses. The rest were development runs.
Inside the engine, Verus is 90 to 93% of worker time.

Estimated: the model's own work was reading the release, writing and debugging `witness.py`, and analysis. It
overlapped with Verus for perhaps 40 minutes, and the model worked alone for about 27 minutes when nothing was
running. That is roughly 45% of wall time with the model active against 82% with Verus active. The model wrote 17
literal witnesses by hand: 9 for fixtures and the control, 8 for dev census lemmas, of which 7 refuted. The
mechanical proposer produced every other verdict: 1,079 holdout, 121 dev variant and 306 dev census refutations.
By verdict count the model tier contributed about 1%. Its role was to show that the template handles classes the
mechanical proposer does not reach, and to read undecided lemmas to tell proof cases from misses.

## Reproducing

```bash
# Release root, archives checked against downloads/manifest.json; Verus 0.2025.09.25.04e8687 and Rust 1.88.0 on PATH
python3.11 analysis/witness.py --release /path/to/release --jobs jobs.jsonl --out out.jsonl --evidence ev/ --workers 4
python3 analysis/gate2_report.py --variants-dev dev.jsonl --variants-holdout holdout.jsonl --out results/gate2
```

A job line holds `sample`, `generated`, `reference`, `task_reference` (the task's file under `data/references`, used
to find `data/io`), `function`, `directions`, `forms` and, optionally, `only_status: ["invalid"]` to search only
rejected lemmas. `--proposals` takes hand-written literals: `{"key": ..., "inputs": {...}, "post": {...},
"output": {...}}`. Variant jobs use the mutant as `generated` and the base as `reference`, as the release's
confirmation does.
