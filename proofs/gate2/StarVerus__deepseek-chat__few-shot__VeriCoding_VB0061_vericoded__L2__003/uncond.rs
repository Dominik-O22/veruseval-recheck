proof fn lemma_b6_all_zero_str2int(s: Seq<char>)
    requires forall|i: int| 0 <= i < s.len() ==> s[i] == '0',
    ensures str2int(s) == 0,
    decreases s.len(),
{
    if s.len() > 0 {
        let t = s.subrange(0, s.len() - 1);
        assert forall|i: int| 0 <= i < t.len() implies t[i] == '0' by {
            assert(t[i] == s[i]);
        }
        lemma_b6_all_zero_str2int(t);
        assert(s[s.len() - 1] == '0');
    }
}
// ---- body
assert forall|i: int| 0 <= i < __ret0@.len() implies __ret0@[i] == '0' by {
    assert(__ret0[i] == __ret0@[i]);
}
lemma_b6_all_zero_str2int(__ret0@);
