// ---- body
let i = choose|i: int| 0 <= i < __arg0.len() && __ret0 === #[trigger] &__arg0[i];
assert(__ret0@ =~= __arg0[i]@);
assert(0 <= i < __arg0.len() && __ret0@ =~= __arg0[i]@);
