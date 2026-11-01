proof fn lemma_max_props(s: Seq<i32>)
    requires s.len() > 0,
    ensures
        forall|i: int| 0 <= i < s.len() ==> s[i] <= max_rcur(s),
        exists|k: int| 0 <= k < s.len() && s[k] == max_rcur(s),
    decreases s.len(),
{
    if s.len() <= 1 {
        assert(s.first() == s[0]);
        assert(s[0] == max_rcur(s));
    } else {
        let t = s.drop_last();
        lemma_max_props(t);
        assert forall|i: int| 0 <= i < s.len() implies s[i] <= max_rcur(s) by {
            if i < s.len() - 1 {
                assert(t[i] == s[i]);
            } else {
                assert(s.last() == s[i]);
            }
        }
        if s.last() >= max_rcur(t) {
            assert(s[s.len() - 1] == max_rcur(s));
        } else {
            let k = choose|k: int| 0 <= k < t.len() && t[k] == max_rcur(t);
            assert(s[k] == t[k]);
            assert(s[k] == max_rcur(s));
        }
    }
}

proof fn lemma_min_props(s: Seq<i32>)
    requires s.len() > 0,
    ensures
        forall|i: int| 0 <= i < s.len() ==> min_rcur(s) <= s[i],
        exists|k: int| 0 <= k < s.len() && s[k] == min_rcur(s),
    decreases s.len(),
{
    if s.len() <= 1 {
        assert(s.first() == s[0]);
        assert(s[0] == min_rcur(s));
    } else {
        let t = s.drop_last();
        lemma_min_props(t);
        assert forall|i: int| 0 <= i < s.len() implies min_rcur(s) <= s[i] by {
            if i < s.len() - 1 {
                assert(t[i] == s[i]);
            } else {
                assert(s.last() == s[i]);
            }
        }
        if s.last() <= min_rcur(t) {
            assert(s[s.len() - 1] == min_rcur(s));
        } else {
            let k = choose|k: int| 0 <= k < t.len() && t[k] == min_rcur(t);
            assert(s[k] == t[k]);
            assert(s[k] == min_rcur(s));
        }
    }
}
// ---- body
let s = __arg0@;
let (mi, ma) = choose|min_idx: int, max_idx: int|
    0 <= min_idx < __arg0.len() && 0 <= max_idx < __arg0.len() &&
    __arg0[min_idx] == __ret0 - __arg0[max_idx] && __arg0[max_idx] == __ret0 - __arg0[min_idx] &&
    forall|i: int| 0 <= i < __arg0.len() ==> __arg0[min_idx] <= __arg0[i] && __arg0[i] <= __arg0[max_idx];
lemma_max_props(s);
lemma_min_props(s);
assert(s[ma] <= max_rcur(s));
let k1 = choose|k: int| 0 <= k < s.len() && s[k] == max_rcur(s);
assert(__arg0[k1] <= __arg0[ma]);
assert(max_rcur(s) == s[ma]);
let k2 = choose|k: int| 0 <= k < s.len() && s[k] == min_rcur(s);
assert(__arg0[mi] <= __arg0[k2]);
assert(min_rcur(s) == s[mi]);
