# Hand check of the failure rule

60 failures sampled with seed 20261102 and read by Claude, not by a person. The first version of the rule read echoed source and agreed with that reading on 56 of 60. A later review showed it overcounts, because the words it matches can sit in the quoted code. The rule now reads only the diagnostic's own words and reports the wider version beside it, 57.8% and 79.3%.

On this sample the narrow rule agrees on 42 of 60. Nearly all its misses are syntax errors inside `requires`, `ensures` or `forall` whose message says only something like "expected `,`". So the wide figure looks closer on this sample, but it was not checked on a fresh one, and the plan reports the range.
