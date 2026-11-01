proof fn lem_b3_filter_all(s: Seq<u32>, p: spec_fn(u32) -> bool)
    requires
        forall|k: int| 0 <= k < s.len() ==> p(#[trigger] s[k]),
    ensures
        s.filter(p) == s,
    decreases s.len(),
{
    reveal(Seq::filter);
    if s.len() == 0 {
        assert(s.filter(p) =~= s);
    } else {
        let t = s.drop_last();
        assert forall|k: int| 0 <= k < t.len() implies p(#[trigger] t[k]) by {
            assert(t[k] == s[k]);
        }
        lem_b3_filter_all(t, p);
        assert(p(s.last()));
        assert(t.push(s.last()) =~= s);
    }
}

// ---- body
match __ret0 {
    Some(idx) => {
        let s = __arg0@.take(idx as int);
        assert forall|k: int| 0 <= k < s.len() implies (|x: u32| x % 2 == 0)(#[trigger] s[k]) by {
            assert(s[k] == __arg0[k]);
        }
        lem_b3_filter_all(s, |x: u32| x % 2 == 0);
        assert(s == s.filter(|x: u32| x % 2 == 0));
    },
    None => {},
}
