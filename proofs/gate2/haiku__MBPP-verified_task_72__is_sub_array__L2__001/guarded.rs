// ---- body
let m = __arg0@;
let s = __arg1@;
if exists|k: int| 0 <= k <= (__arg0.len() as int) - (__arg1.len() as int) && #[trigger] matches_at(m, s, k) {
    let k = choose|k: int| 0 <= k <= (__arg0.len() as int) - (__arg1.len() as int) && #[trigger] matches_at(m, s, k);
    let l = k + s.len();
    assert(m.subrange(k, l) =~= s);
    assert(0 <= k <= (__arg0.len() - __arg1.len()) && l == k + __arg1.len() && m.subrange(k, l) =~= s);
} else {
    assert forall|k: int, l: int|
        !(0 <= k <= (__arg0.len() - __arg1.len()) && l == k + __arg1.len() && #[trigger] m.subrange(k, l) =~= s) by {
        if 0 <= k <= (__arg0.len() - __arg1.len()) && l == k + __arg1.len() && m.subrange(k, l) =~= s {
            assert forall|j: int| 0 <= j < s.len() implies m[k + j] == s[j] by {
                assert(m.subrange(k, l)[j] == m[k + j]);
            }
            assert(matches_at(m, s, k));
        }
    }
}
