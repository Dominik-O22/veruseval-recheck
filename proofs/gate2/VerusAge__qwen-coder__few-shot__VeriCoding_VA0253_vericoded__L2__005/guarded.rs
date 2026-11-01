// ---- body
let am = __arg2@.map(|i: int, x: i8| x as int);
if __arg2.len() >= 1 {
    assert(am[0] == __arg2@[0] as int);
}
