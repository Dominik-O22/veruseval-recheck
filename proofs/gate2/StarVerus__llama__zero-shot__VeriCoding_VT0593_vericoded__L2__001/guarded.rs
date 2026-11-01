// ---- body
let m = __arg0@.map(|i, x: i8| x as int);
let w = choose|i: int| (0 <= i && i < __arg0.len() as int) && (__ret0 == __arg0[i]);
assert(m.len() == __arg0.len());
assert(m[w] == __arg0[w] as int);
assert forall|j: int| 0 <= j < m.len() implies __ret0 as int <= #[trigger] m[j] by {
    assert(m[j] == __arg0[j] as int);
    assert(__ret0 <= __arg0[j]);
}
assert(0 <= w < m.len() && __ret0 as int == m[w] && forall|j: int| 0 <= j < m.len() ==> __ret0 as int <= m[j]);
assert(is_min_of_all(__ret0 as int, m));
