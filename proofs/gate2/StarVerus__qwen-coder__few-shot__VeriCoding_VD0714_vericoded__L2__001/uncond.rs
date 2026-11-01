// ---- body
let pred = |x: i32| x % 2 == 0;
let s = __arg0@;
let fl = s.filter(pred);
s.filter_lemma(pred);
assert(__ret0@ == fl);
assert forall|i: int| 0 <= i < __ret0.len() implies is_even(__ret0[i] as int) && __arg0@.contains(__ret0[i]) by {
    assert(__ret0[i] == fl[i]);
    assert(pred(fl[i]));
    assert(fl.contains(fl[i]));
    s.lemma_filter_contains_rev(pred, fl[i]);
}
