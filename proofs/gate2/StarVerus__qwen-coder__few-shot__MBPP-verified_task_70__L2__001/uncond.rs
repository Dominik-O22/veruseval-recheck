proof fn lemma_cti_bounds(s: Seq<bool>, i: int)
    requires 0 <= i <= s.len(),
    ensures 0 <= count_true_impl(s, i) <= s.len() - i,
    decreases s.len() - i,
{
    if i < s.len() {
        lemma_cti_bounds(s, i + 1);
    }
}
// ---- body
lemma_cti_bounds(__arg0@, 0);
