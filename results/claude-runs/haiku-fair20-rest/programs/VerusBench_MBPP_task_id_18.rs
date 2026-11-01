use vstd::prelude::*;

fn main() {}

verus! {

proof fn lemma_push_facts(s: Seq<u8>, x: u8)
    ensures
        s.push(x).len() == s.len() + 1,
        s.push(x)[s.len() as int] == x,
        forall|k: int| 0 <= k < s.len() ==> #[trigger] s.push(x)[k] == s[k],
{
}

proof fn lemma_contains_last(s: Seq<u8>, x: u8)
    ensures
        s.push(x).contains(x),
{
    lemma_push_facts(s, x);
    assert(0 <= s.len() && s.len() < s.push(x).len() && s.push(x)[s.len() as int] == x);
}

proof fn lemma_push_contains_elem(s: Seq<u8>, x: u8, y: u8)
    requires
        s.contains(y),
    ensures
        s.push(x).contains(y),
{
    let k = choose|k: int| 0 <= k < s.len() && s[k] == y;
    lemma_push_facts(s, x);
    assert(s.push(x)[k] == s[k]);
    assert(0 <= k < s.push(x).len() && s.push(x)[k] == y);
}

proof fn lemma_contains_at(s: Seq<u8>, i: int)
    requires
        0 <= i < s.len(),
    ensures
        s.contains(s[i]),
{
    assert(0 <= i < s.len() && s[i] == s[i]);
}

fn contains(str: &[u8], key: u8) -> (result: bool)
    ensures
        result <==> (exists|i: int| 0 <= i < str@.len() && str@[i] == key),
{
    let mut i = 0;
    while i < str.len()
        invariant
            forall|m: int| 0 <= m < i ==> str@[m] != key,
        decreases
            str.len() - i
    {
        if (str[i] == key) {
            proof {
                assert(0 <= i as int && (i as int) < str@.len() && str@[i as int] == key);
            }
            return true;
        }
        i += 1;
    }
    proof {
        assert(forall|m: int| 0 <= m < str@.len() ==> str@[m] != key);
    }
    false
}

fn remove_chars(str1: &[u8], str2: &[u8]) -> (result: Vec<u8>)
    ensures
        forall|k: int|
            0 <= k < result@.len() ==> (str1@.contains(#[trigger] result@[k]) && !str2@.contains(
                result@[k],
            )),
        forall|i: int|
            0 <= i < str1@.len() ==> (str2@.contains(#[trigger] str1@[i]) || result@.contains(
                str1@[i],
            )),
{
    let mut output_str = Vec::new();
    let mut index: usize = 0;

    while index < str1.len()
        invariant
            0 <= index <= str1@.len(),
            forall|k: int|
                0 <= k < output_str@.len() ==> (str1@.contains(#[trigger] output_str@[k])
                    && !str2@.contains(output_str@[k])),
            forall|k: int|
                0 <= k < index ==> (str2@.contains(#[trigger] str1@[k]) || output_str@.contains(
                    str1@[k],
                )),
        decreases
            str1.len() - index
    {
        if (!contains(str2, str1[index])) {
            proof {
                let c = str1@[index as int];
                lemma_contains_at(str1@, index as int);
                lemma_contains_last(output_str@, c);
                lemma_push_facts(output_str@, c);
                assert(str1@.contains(c));
                assert(!str2@.contains(c));
                assert forall|k: int| 0 <= k < index as int implies (str2@.contains(
                    #[trigger] str1@[k],
                ) || output_str@.push(c).contains(str1@[k])) by {
                    if !str2@.contains(str1@[k]) {
                        lemma_push_contains_elem(output_str@, c, str1@[k]);
                    }
                }
            }
            output_str.push(str1[index]);
        } else {
            proof {
                assert(str2@.contains(str1@[index as int]));
            }
        }
        index += 1;
    }
    output_str
}

}