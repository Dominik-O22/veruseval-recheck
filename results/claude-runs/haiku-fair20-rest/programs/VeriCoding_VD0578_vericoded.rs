use vstd::prelude::*;

verus! {

// This spec function checks whether a character is one of the lowercase vowels
spec fn is_lower_vowel(c: char) -> bool {
    c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u'
}

// Helper lemma: filtering a pushed sequence extends the filtered sequence by the pushed element iff it passes the predicate
proof fn lemma_filter_push(s: Seq<char>, x: char)
    ensures
        s.push(x).filter(|c: char| is_lower_vowel(c)) =~= s.filter(|c: char| is_lower_vowel(c)) + (if is_lower_vowel(x) {
            seq![x]
        } else {
            Seq::<char>::empty()
        }),
{
    reveal_with_fuel(Seq::filter, 2);
    assert(s.push(x).drop_last() =~= s);
    assert(s.push(x).last() == x);
}

// Helper lemma: taking one more element equals pushing the next element onto the shorter take
proof fn lemma_take_succ(s: Seq<char>, i: int)
    requires
        0 <= i < s.len(),
    ensures
        s.take(i + 1) =~= s.take(i).push(s[i]),
{
    assert(s.take(i + 1).drop_last() =~= s.take(i));
    assert(s.take(i + 1).last() == s[i]);
}

// Implementation following the ground-truth
fn filter_vowels_array(xs: &[char]) -> (ys: Vec<char>)
    ensures
        ys@ == xs@.filter(|c: char| is_lower_vowel(c)),
{
    let mut result: Vec<char> = Vec::new();
    let mut i: usize = 0;
    assert(xs@.take(0int).filter(|c: char| is_lower_vowel(c)) =~= Seq::<char>::empty()) by {
        reveal_with_fuel(Seq::filter, 2);
    };
    while i < xs.len()
        invariant
            0 <= i as int <= xs@.len(),
            result@ == xs@.take(i as int).filter(|c: char| is_lower_vowel(c)),
        decreases
            xs.len() - i,
    {
        let c = xs[i];
        proof {
            lemma_take_succ(xs@, i as int);
            lemma_filter_push(xs@.take(i as int), xs@[i as int]);
        }
        if c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u' {
            result.push(c);
        } else {
        }
        i = i + 1;
    }
    proof {
        assert(xs@.take(xs@.len() as int) =~= xs@);
    }
    result
}

fn main() {}
}