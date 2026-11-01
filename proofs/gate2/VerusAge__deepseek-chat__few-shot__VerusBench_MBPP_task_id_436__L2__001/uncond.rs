proof fn neg_eq_filter(s: Seq<i32>)
    ensures negative_elements(s) == s.filter(|x: i32| x < 0),
    decreases s.len(),
{
    reveal(Seq::filter);
    if s.len() > 0 {
        neg_eq_filter(s.drop_last());
    }
}
// ---- body
neg_eq_filter(__arg0@);
