proof fn lemma_fv_eq_filter(s: Seq<char>)
    ensures filter_vowels(s) == s.filter(|c: char| is_lower_vowel(c))
    decreases s.len()
{
    reveal(Seq::filter);
    if s.len() > 0 {
        let p = s.subrange(0, s.len() - 1);
        assert(s.drop_last() =~= p);
        lemma_fv_eq_filter(p);
        let c = s[s.len() - 1];
        assert(vowels().contains(c) == is_lower_vowel(c));
        assert(s.last() == c);
        if is_lower_vowel(c) {
            assert(p.filter(|c: char| is_lower_vowel(c)).add(seq![c]) =~= p.filter(|c: char| is_lower_vowel(c)).push(c));
        }
    } else {
        assert(s.filter(|c: char| is_lower_vowel(c)) =~= Seq::<char>::empty());
        assert(filter_vowels(s) =~= Seq::<char>::empty());
    }
}
// ---- body
lemma_fv_eq_filter(__arg0@);
