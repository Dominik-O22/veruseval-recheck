proof fn lemma_cm_eq(s: Seq<i8>, k: int)
    requires
        0 <= k <= s.len() as int / 2,
    ensures
        count_mismatches(s, k) == count_mismatched_pairs_up_to(s.map(|i, x| x as int), k),
    decreases k
{
    let m = s.map(|i, x| x as int);
    assert(m.len() == s.len());
    if k > 0 {
        lemma_cm_eq(s, k - 1);
        assert(m[k - 1] == s[k - 1] as int);
        assert(m[s.len() - k] == s[s.len() - k] as int);
    }
}
// ---- body
lemma_cm_eq(__arg0@, __arg0@.len() as int / 2);
assert(count_mismatched_pairs(__arg0@.map(|i, x| x as int)) == count_mismatched_pairs_up_to(__arg0@.map(|i, x| x as int), __arg0@.len() as int / 2));
