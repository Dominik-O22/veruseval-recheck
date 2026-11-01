proof fn lemma_cti_cb(s: Seq<bool>, i: int)
    requires 0 <= i <= s.len(),
    ensures count_true_impl(s, i) + count_boolean(s.subrange(0, i)) == count_boolean(s),
    decreases s.len() - i,
{
    if i >= s.len() {
        assert(s.subrange(0, i) =~= s);
    } else {
        lemma_cti_cb(s, i + 1);
        assert(s.subrange(0, i + 1).drop_last() =~= s.subrange(0, i));
        assert(s.subrange(0, i + 1).last() == s[i]);
    }
}
// ---- body
lemma_cti_cb(__arg0@, 0);
assert(__arg0@.subrange(0, 0) =~= Seq::<bool>::empty());
assert(count_boolean(__arg0@.subrange(0, 0)) == 0);
