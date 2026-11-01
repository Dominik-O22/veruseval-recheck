### variant_gate.csv

| split | forms | must_refute | refuted | recall | must_clear_rows | unexpected_refutations |
|---|---|---|---|---|---|---|
| dev | paper form (L1, unconditional L2) | 81 | 81 | 1.0 | 97 | 0 |
| dev | guarded L2 in place of unconditional | 81 | 81 | 1.0 | 97 | 0 |
| holdout | paper form (L1, unconditional L2) | 728 | 719 | 0.9876 | 980 | 0 |
| holdout | guarded L2 in place of unconditional | 728 | 713 | 0.9794 | 980 | 0 |

### variant_recall_by_operator.csv

| split | form | operator | must_refute | refuted | missed | recall | must_clear | cleared | unexpected_refutations |
|---|---|---|---|---|---|---|---|---|---|
| dev | single | PRE_ADD | 19 | 19 | 0 | 1.0 | 0 | 0 | 0 |
| dev | single | PRE_REFINE | 22 | 22 | 0 | 1.0 | 0 | 0 | 0 |
| dev | single | PRE_REMOVE | 0 | 0 | 0 |  | 2 | 2 | 0 |
| dev | single | PRE_RELAX | 0 | 0 | 0 |  | 1 | 1 | 0 |
| dev | single | POST_ADD | 0 | 0 | 0 |  | 5 | 5 | 0 |
| dev | single | POST_REMOVE | 0 | 0 | 0 |  | 22 | 22 | 0 |
| dev | single | POST_RELAX | 0 | 0 | 0 |  | 18 | 18 | 0 |
| dev | unconditional | PRE_ADD | 0 | 0 | 0 |  | 19 | 19 | 0 |
| dev | unconditional | PRE_REFINE | 0 | 0 | 0 |  | 22 | 22 | 0 |
| dev | unconditional | PRE_REMOVE | 0 | 0 | 0 |  | 2 | 2 | 0 |
| dev | unconditional | PRE_RELAX | 0 | 0 | 0 |  | 1 | 1 | 0 |
| dev | unconditional | POST_ADD | 0 | 0 | 0 |  | 5 | 5 | 0 |
| dev | unconditional | POST_REMOVE | 22 | 22 | 0 | 1.0 | 0 | 0 | 0 |
| dev | unconditional | POST_RELAX | 18 | 18 | 0 | 1.0 | 0 | 0 | 0 |
| dev | guarded | PRE_ADD | 0 | 0 | 0 |  | 19 | 19 | 0 |
| dev | guarded | PRE_REFINE | 0 | 0 | 0 |  | 22 | 22 | 0 |
| dev | guarded | PRE_REMOVE | 0 | 0 | 0 |  | 2 | 2 | 0 |
| dev | guarded | PRE_RELAX | 0 | 0 | 0 |  | 1 | 1 | 0 |
| dev | guarded | POST_ADD | 0 | 0 | 0 |  | 5 | 5 | 0 |
| dev | guarded | POST_REMOVE | 22 | 22 | 0 | 1.0 | 0 | 0 | 0 |
| dev | guarded | POST_RELAX | 18 | 18 | 0 | 1.0 | 0 | 0 | 0 |
| holdout | single | PRE_ADD | 144 | 144 | 0 | 1.0 | 0 | 0 | 0 |
| holdout | single | PRE_REFINE | 209 | 209 | 0 | 1.0 | 0 | 0 | 0 |
| holdout | single | PRE_REMOVE | 0 | 0 | 0 |  | 33 | 33 | 0 |
| holdout | single | PRE_RELAX | 0 | 0 | 0 |  | 26 | 26 | 0 |
| holdout | single | POST_ADD | 0 | 0 | 0 |  | 64 | 64 | 0 |
| holdout | single | POST_REFINE | 0 | 0 | 0 |  | 3 | 3 | 0 |
| holdout | single | POST_REMOVE | 0 | 0 | 0 |  | 202 | 202 | 0 |
| holdout | single | POST_RELAX | 0 | 0 | 0 |  | 173 | 173 | 0 |
| holdout | unconditional | PRE_ADD | 0 | 0 | 0 |  | 144 | 144 | 0 |
| holdout | unconditional | PRE_REFINE | 0 | 0 | 0 |  | 209 | 209 | 0 |
| holdout | unconditional | PRE_REMOVE | 0 | 0 | 0 |  | 33 | 33 | 0 |
| holdout | unconditional | PRE_RELAX | 0 | 0 | 0 |  | 26 | 26 | 0 |
| holdout | unconditional | POST_ADD | 0 | 0 | 0 |  | 64 | 64 | 0 |
| holdout | unconditional | POST_REFINE | 0 | 0 | 0 |  | 3 | 3 | 0 |
| holdout | unconditional | POST_REMOVE | 202 | 194 | 8 | 0.9604 | 0 | 0 | 0 |
| holdout | unconditional | POST_RELAX | 173 | 172 | 1 | 0.9942 | 0 | 0 | 0 |
| holdout | guarded | PRE_ADD | 0 | 0 | 0 |  | 144 | 144 | 0 |
| holdout | guarded | PRE_REFINE | 0 | 0 | 0 |  | 209 | 209 | 0 |
| holdout | guarded | PRE_REMOVE | 0 | 0 | 0 |  | 33 | 33 | 0 |
| holdout | guarded | PRE_RELAX | 0 | 0 | 0 |  | 26 | 26 | 0 |
| holdout | guarded | POST_ADD | 0 | 0 | 0 |  | 64 | 64 | 0 |
| holdout | guarded | POST_REFINE | 0 | 0 | 0 |  | 3 | 3 | 0 |
| holdout | guarded | POST_REMOVE | 202 | 192 | 10 | 0.9505 | 0 | 0 | 0 |
| holdout | guarded | POST_RELAX | 173 | 168 | 5 | 0.9711 | 0 | 0 | 0 |

### variant_unexpected_refutations.csv

(none)

### both_verdicts.csv

(none)

### type_classes.csv

| source | type_class | lemmas | searched | refuted | unsupported_type | no_harness | engine_error | all_screens_failed_to_compile | void_controls | inconclusive_controls | realized | unrepresentable | realization_not_run | release_rejected | release_rejected_refuted |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| variants_dev | &mut/old | 94 | 94 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 9 | 9 |
| variants_dev | Option | 4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 |
| variants_dev | Vec | 466 | 466 | 94 | 0 | 0 | 0 | 0 | 0 | 0 | 94 | 0 | 0 | 94 | 94 |
| variants_dev | bool | 20 | 20 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 6 | 6 |
| variants_dev | integer | 557 | 557 | 121 | 0 | 0 | 0 | 0 | 0 | 0 | 121 | 0 | 0 | 121 | 121 |
| variants_dev | slice | 12 | 12 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 4 | 4 |
| variants_holdout | &mut/old | 1599 | 1599 | 191 | 0 | 0 | 0 | 0 | 0 | 0 | 191 | 0 | 0 | 191 | 191 |
| variants_holdout | Vec | 4587 | 4587 | 969 | 0 | 0 | 0 | 0 | 0 | 0 | 915 | 0 | 54 | 987 | 969 |
| variants_holdout | bool | 424 | 424 | 123 | 0 | 0 | 0 | 0 | 0 | 0 | 123 | 0 | 0 | 123 | 123 |
| variants_holdout | char | 465 | 465 | 123 | 0 | 0 | 0 | 0 | 0 | 0 | 123 | 0 | 0 | 125 | 123 |
| variants_holdout | int/nat | 278 | 278 | 79 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 71 | 80 | 79 |
| variants_holdout | integer | 4357 | 4357 | 892 | 0 | 0 | 0 | 0 | 0 | 0 | 869 | 0 | 23 | 914 | 892 |
| variants_holdout | recursive spec fn | 26 | 26 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 10 | 10 |
| variants_holdout | slice | 372 | 372 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 70 | 0 | 20 | 90 | 90 |
| variants_holdout | string | 40 | 40 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 12 | 6 |
| variants_holdout | tuple | 46 | 46 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 8 | 1 |
| fixtures | Option | 8 | 8 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 2 |
| fixtures | Vec | 8 | 8 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 0 | 3 | 3 |
| fixtures | array | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 |
| fixtures | bool | 18 | 18 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 1 | 0 | 7 | 7 |
| fixtures | char | 4 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 2 |
| fixtures | enum | 8 | 8 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 2 |
| fixtures | float | 7 | 7 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 3 | 3 |
| fixtures | integer | 42 | 42 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 1 | 0 | 13 | 13 |
| fixtures | string | 11 | 11 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 5 | 5 |
| fixtures | struct | 4 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 |
| fixtures | tuple | 8 | 8 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 2 |
| census_dev | &mut/old | 31 | 31 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 1 | 0 | 31 | 11 |
| census_dev | Option | 67 | 67 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 67 | 4 |
| census_dev | Vec | 745 | 716 | 230 | 29 | 0 | 0 | 0 | 0 | 0 | 218 | 12 | 0 | 745 | 230 |
| census_dev | array | 7 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 7 | 1 |
| census_dev | bool | 117 | 88 | 26 | 29 | 0 | 0 | 0 | 0 | 0 | 22 | 4 | 0 | 117 | 26 |
| census_dev | char | 113 | 113 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 2 | 0 | 113 | 14 |
| census_dev | float | 120 | 120 | 68 | 0 | 0 | 0 | 0 | 0 | 0 | 67 | 1 | 0 | 120 | 68 |
| census_dev | int/nat | 14 | 14 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 14 | 2 |
| census_dev | integer | 791 | 791 | 238 | 0 | 0 | 0 | 0 | 0 | 0 | 229 | 9 | 0 | 791 | 238 |
| census_dev | recursive spec fn | 136 | 121 | 4 | 15 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 136 | 4 |
| census_dev | slice | 143 | 143 | 33 | 0 | 0 | 0 | 0 | 0 | 0 | 33 | 0 | 0 | 143 | 33 |
| census_dev | struct | 40 | 40 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 40 | 3 |
| census_dev | tuple | 13 | 13 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 13 | 3 |
| census_dev | unsupported | 45 | 0 | 0 | 45 | 0 | 0 | 0 | 0 | 0 |  |  |  | 45 | 0 |
| control | bool | 4 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 2 |
| control | integer | 4 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 2 | 2 |

### timing.csv

| source | outcome | checks | mean_s | median_s | p90_s | max_s | total_s |
|---|---|---|---|---|---|---|---|
| variants_dev | refuted | 121 | 2.743 | 2.711 | 3.343 | 4.422 | 332.0 |
| variants_dev | undecided | 436 | 1.487 | 1.401 | 2.183 | 4.283 | 648.2 |
| variants_holdout | refuted | 1079 | 2.626 | 2.519 | 3.242 | 11.655 | 2833.0 |
| variants_holdout | undecided | 3961 | 1.544 | 1.303 | 1.968 | 174.196 | 6115.3 |
| fixtures | refuted | 19 | 2.074 | 2.083 | 2.328 | 2.419 | 39.4 |
| fixtures | undecided | 35 | 0.578 | 0.477 | 0.983 | 1.078 | 20.2 |
| census_dev | refuted | 306 | 2.522 | 2.42 | 3.136 | 4.397 | 771.8 |
| census_dev | undecided | 661 | 1.244 | 1.09 | 1.793 | 5.566 | 822.3 |
| control | refuted | 2 | 2.139 | 2.139 | 2.366 | 2.234 | 4.3 |
| control | undecided | 2 | 0.922 | 0.922 | 1.364 | 1.106 | 1.8 |

