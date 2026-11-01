proof fn lemma_gcd_eq_spec(x: int, y: int)
    requires x > 0, y > 0,
    ensures gcd(x, y) == gcd_spec(x, y),
    decreases x + y,
{
    if x == y {
    } else if x > y {
        lemma_gcd_eq_spec(x - y, y);
    } else {
        lemma_gcd_eq_spec(x, y - x);
    }
}
// ---- body
lemma_gcd_eq_spec(__arg0, __arg1);
