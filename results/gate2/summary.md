# Gate 2: proving and refuting rejected clause lemmas (development run)

Date: 1 November 2026. Branch `gate2-proofs`. Verus 0.2025.09.25.04e8687, Rust 1.88.0, installed directly from the release Dockerfile's pinned, hash-checked steps (no Docker image). Release archives reassembled from `downloads/manifest.json`; every part and both archives match their SHA-256.

Per-clause rows: [`clauses.csv`](clauses.csv), keyed by sample ID and check name. Proof text and witnesses: [`proofs/gate2/<id>/`](../../proofs/gate2). No harness is committed, because harnesses embed the release's references.

## Method

- **Regeneration.** [`analysis/gate2_regenerate.py`](../../analysis/gate2_regenerate.py) re-runs the release's per-clause path (`metrics_rebuild.share.smt.clause_implication_metric`, as `gate1_regenerate.py` does) and captures the exact harness Verus checks. The unconditional form is the release's own lemma. The guarded form is the same call with the reference and generated `requires` prepended to the antecedent. For L1 the two forms are one formula. Of the 117 clauses with a released record, **117 of 117** regenerate with the same obligation context and the same `invalid` status. LLM calls are disabled in the regenerator.
- **Checker.** [`analysis/gate2_check.py`](../../analysis/gate2_check.py).
  - A proof is spliced into the unchanged lemma, and the whole file is verified. The text may not contain `assume`, `admit`, `external_body`, `#[verifier`, `axiom`, `uninterp`, `unsafe`, `opaque` or `trusted`. `--rlimit 100` is allowed.
  - A refutation takes literal values only. A fixed template binds them in an exec fn with no loops, branches or calls, using `vec![..]`, tuples and struct literals. It asserts every antecedent wrapper and the negated consequent. A second run replaces the asserts with `assert(false)`, and a verdict is void if that also verifies. That never happened.
  - Because the values are built by exec code, every refutation is a representable input and output.
- **Tiers.** Tier 0, with no model: an empty body, `--rlimit 100`, and `reveal_with_fuel` on recursive spec fns. After that, proofs and witnesses were written in this session by 8 subagents, one per batch grouped by task, plus 4 clauses I did directly. The rules were: stop at the first verdict on each form, make at least 3 genuine attempts on each side before Undecided, and run the checker at most 12 times per form.
- **Re-check.** [`analysis/gate2_report.py`](../../analysis/gate2_report.py) re-runs every claimed proof and witness through the checker. That includes the propagation runs, where a guarded witness is re-run on the unconditional harness. **0 of the claimed verdicts failed the re-check.**

## Populations

| Set | Clauses | Note |
|---|---|---|
| regrade-14: rejected L2 clauses of the 14 `checker_wrong` rows | 17 | 14 rows |
| Haiku: invalid unconditional L2 in `haiku-fair20` and `haiku-fair20-rest` | 12 | 7 tasks, 8 functions; no released record, so no context match is possible |
| dev100: seeded sample (seed 20261102) of rejected L1/L2 clauses on dev tasks | 100 (23 L1, 77 L2) | pool of 656 (144 L1, 512 L2) on 457 accepted artifacts, 108 tasks |

One dev100 clause (VerusAge deepseek-chat VT0269 `L2__003`) is also a regrade-14 clause. It was searched once and is counted in both sets: 128 unique clauses.

## Results: guarded × unconditional grid

Each cell is guarded / unconditional. P = proved, R = refuted, U = undecided.

| Set | P/P solver limit | P/R premise only | R/R difference | P/U guarded only | U/R certified false, unlocated | U/U | R/P (must be empty) |
|---|---|---|---|---|---|---|---|
| regrade-14, by clause (17) | 5 | 10 | 0 | 2 | 0 | 0 | 0 |
| regrade-14, by row (14) | 5 | 7 | 0 | 2 | 0 | 0 | 0 |
| Haiku L2 (12) | 10 | 0 | 0 | 2 | 0 | 0 | 0 |
| dev100 L2 (77) | 30 | 21 | 12 | 10 | 1 | 3 | 0 |
| dev100 L1 (23, one form) | 2 proved | — | 13 refuted | — | — | 8 undecided | — |

- **task_73** comes out as expected: guarded proved (tier 0, empty body) and unconditional refuted by `n = 0, result = true`, on the first try.
- **regrade-14 rows.**
  - Premise only (7): MBPP_73, VT0044, VJ0001, VJ0142, VA0123, CloverBench is_prime, VA0383.
  - Unconditionally proved, which is a solver limit (5): MBPP_47, VB0061, VS0054, VD0044, VT0269.
  - Undecided in the unconditional form (2): VA0523, where the only open case is `k = 0` and `n % 0` is unspecified, and DAFNY79, where the `len as i32` truncation needs a slice of at least 2^31 elements.
- **Haiku.** All 12 clauses are proved in the guarded form. Unconditionally, 10 of 12 are proved. The 2 undecided are `task_72 sub_array_at_index`, a `subrange` past the end, which is unspecified, and `VA0115 solve`, which reads `presidents()` past its end. At function level, 6 of the 8 functions have every rejected L2 clause proved unconditionally.
- **dev100 L2 (77).**
  - Unconditional: 30 proved, 34 refuted, 13 undecided.
  - Guarded: 61 proved, 12 refuted, 4 undecided.
  - Rejected L2 that are premise only: 21 of 77 (27%), above the plan's 20% guess.
- **dev100 L1 (23).** 2 proved, 13 refuted, 8 undecided.
- **dev100 overall, unconditional (the paper's obligation).** 32 proved, 47 refuted, 21 undecided, out of 100.

## By type class (dev100, n = 100)

The type class is taken from the lemma parameter types, first match in this order: float, spec int/collection, char/string, nested collection, int/bool collection, struct/enum/generic, scalar.

| Type class | n | Uncond proved | Uncond refuted | Uncond undecided | Guarded proved | Guarded refuted | Guarded undecided |
|---|---|---|---|---|---|---|---|
| int/bool collection | 44 | 16 | 20 | 8 | 30 | 12 | 2 |
| float | 18 | 1 | 9 | 8 | 8 | 4 | 6 |
| scalar | 17 | 6 | 10 | 1 | 12 | 5 | 0 |
| char/string | 11 | 5 | 3 | 3 | 5 | 2 | 4 |
| spec int/collection | 5 | 3 | 1 | 1 | 4 | 1 | 0 |
| struct/enum/generic | 3 | 0 | 3 | 0 | 3 | 0 | 0 |
| nested collection | 2 | 1 | 1 | 0 | 1 | 1 | 0 |
| **all** | **100** | **32** | **47** | **21** | **63** | **25** | **12** |

The 23 clauses with a recursive spec fn split 13 proved, 6 refuted and 4 undecided (unconditional). For L1 the guarded columns repeat the one form.

Floats are the weakest class: 8 of 18 are undecided unconditionally, and only 1 is proved. Refutations on floats succeed when the clause turns on lengths or indices.

## Why the 21 unconditional undecided stayed undecided

These are the subagents' explanations, and no verdict rests on them:

- **Unspecified values.** Out-of-bounds sequence reads, `subrange` past the end, `n % 0`, `char as u8` above 255, and recursive spec fns outside their `decreases` domain. Verus leaves these values unspecified, so neither a proof nor a literal witness can settle the clause.
- **Length bounds.** `len <= usize::MAX/2`, `len < usize::MAX`, `len <= 2^31-1`, `len <= 1000000` and similar. These hold for any real Vec but cannot be proved from vstd's `len <= usize::MAX`. A witness would need an enormous vector: the literal grammar rejects `vec![x; n]`, and a 1,000,001-element literal hits the checker's 300 s timeout. Under the plan these belong to the "unrepresentable inputs" class.
- **Floats.** Values that are largely uninterpreted.
- **Template limits.** Antecedents that need two separately bound `Vec`s to be equal, such as VT0457's `result.coef == coefficients`. The template binds each parameter separately, and Verus has no `Vec` extensionality. A few others are trigger problems: an explicit trigger that literal values never instantiate, and `!exists` over mapped sequences.

## Effort and which try produced the verdict

- **Tries (dev100, unconditional form).** Of the 79 verdicts, 72 came on try 1, 4 on try 2 and 3 on try 3. No unconditional verdict came from tier 0.
- **Tries (dev100, guarded form).** 25 came from tier 0 with an empty body, 15 are the same formula as the unconditional form, 15 are L1 (one form), 17 propagated from an unconditional proof, 14 came from an agent's try 1 and 2 from try 3. 12 stayed undecided.
- **Self-reported effort per form, all 128 clauses.** Tool calls include reads and checker runs; tokens are the agents' rough estimates of what they read and wrote for that form.

  | Outcome | Forms | Mean tool calls | Mean checker runs | Mean rough tokens |
  |---|---|---|---|---|
  | uncond proved | 46 | 2.0 | 1.0 | 4,100 |
  | uncond refuted | 57 | 2.2 | 1.1 | 4,100 |
  | uncond undecided | 25 | 5.3 | 5.9 | 12,900 |
  | guarded proved (agent) | 8 | 2.5 | 1.0 | 6,300 |
  | guarded refuted | 10 | 2.2 | 1.2 | 4,300 |
  | guarded undecided | 1 | 8.0 | 6.0 | 14,000 |

  Totals: 171 forms searched, 450 tool calls, 311 checker runs, about 0.96M self-reported tokens.
- **Measured agent usage.** The harness reports each batch agent's final context size and its tool uses:

  | Batch | Final context (tokens) | Tool uses |
  |---|---|---|
  | 0 | 72k | 32 |
  | 1 | 80k | 40 |
  | 2 | 84k | 33 |
  | 3 | 87k | 42 |
  | 4 | 91k | 44 (+8 before the checker fix) |
  | 5 | 97k | 44 |
  | 6 | 98k | 47 (+7 before the fix) |
  | 7 | 101k | 46 (+9 before the fix) |

  The self-reported figures leave out the context that is re-read on every turn. An agent turn re-reads its whole context, so the input actually processed is roughly the number of tool uses times the mean context. That is about Σ tool uses × final context ÷ 2 ≈ **15M input tokens** for the 128 clauses (≈115k per clause), most of it cacheable. Output tokens were not measured separately.

## Estimate for all 3,043 rejected clause lemmas

Scaling these per-clause figures by 3,043 / 128 ≈ 23.8, under the same protocol (agentic, stop at the first verdict on each form):

- **Self-reported marginal tokens:** ≈ 7.5k per clause, so ≈ **23M tokens**.
- **Input processed, with context re-reads:** ≈ 115k per clause, so ≈ **350M input tokens**, mostly cache reads. Output adds roughly 5–10% more on top (a guess).
- **Verus time:** negligible, about 1 s per checker run. The exception is very large literal witnesses.

The development sample may be easier or harder than the census, and undecided forms cost about three times as much as decided ones. Treat this as a range of ±50% at least. The plan's $0.05 per obligation came from single-shot API calls and does not apply to this agentic protocol.

## Failures, deviations and known limits

1. **Checker bug, fixed mid-run.** Refute mode first looked for a `} // verus!` line that only 30 of 124 harnesses have, and crashed (`ValueError`) on the rest. The fix appends the witness in its own `verus!` block. Agents re-ran the affected witnesses, crashed runs were not counted, and no form was logged as undecided because of the crash. Batch 5 had run some witnesses on copies of the harnesses with the marker added. It re-ran them on the originals, and the final re-check uses only the originals.
2. **Regenerator bugs, fixed.**
   - The release caches lemma results per process, and pool workers reused that cache. Two items lost their harness, and some guarded forms were served from the cache. The cache is now cleared per item and per form, and everything was re-run.
   - The Haiku item IDs were per function, not per clause, so 4 of the 12 Haiku clauses had their harnesses overwritten (VH0074 `002` and `004`, VT0026 `005`, VT0178 `003`). The IDs are now per clause. The 8 surviving harnesses are byte-identical to the regenerated ones, and the 4 missing clauses were regenerated and searched. All 4 were proved on try 1, by me, with a guarded tier 0 run first.
3. **Fewer than 3 refutation attempts.** On 5 length-bound forms (VT0081 L1 `001` and `002`, DAFNY79 uncond, MBPP task_53 L1, VD0744 L1) the agents ran 0 or 1 refutations, because no representable literal witness exists. On VT0457 one of the three refutation runs was wasted on a bad `_fuel` key. These forms are recorded as undecided.
4. **The forbidden-word filter matches substrings.** It also blocks vstd's own lemmas whose names contain "axiom" (`axiom_spec_len`, `group_vec_axioms`). Those runs were rejected and not counted. This is stricter than the rule requires, and it may have cost proofs on length-bound L1 clauses.
5. **`usize` width.** Verus here does not fix the width of `usize`, so literals above `u32::MAX` do not type-check. One refutation (VB0061 `L1__001`, dev) binds `usize::MAX`, a named constant, which holds at either width. The literal check accepts it, but it is not a numeric literal.
6. **Not done.** The plan's guard check, which requires a witness satisfying both preconditions before a guarded proof counts, was not run. A guarded "proved" here can still be vacuous if the two preconditions conflict. Also not done: validation on the authors' variants, the both-engines soundness run, stability, and the second proposer.
7. **The Haiku status came from a different path.** `unconditional_l2.jsonl` used the `semantic_strength` path with the antecedent reduced. Here the per-clause path was re-run on the same programs and also rejects every one of the 8 functions, giving 12 clauses. There is no released record to match context against.
8. **Not pushed.** The repository has no `origin` in this VM, and the git proxy refused `Dominik-O22/veruseval-recheck` because it is not in the session's authorized repositories. The commits exist only on the local `gate2-proofs` branch.
