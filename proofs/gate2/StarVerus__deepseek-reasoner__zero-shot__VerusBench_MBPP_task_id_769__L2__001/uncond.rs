// ---- body
assert forall|i: int| 0 <= i < __arg0.len() && !__arg1@.contains(#[trigger] __arg0[i]) implies __ret0@.contains(__arg0[i]) by {
    let v = __arg0[i];
    assert(__arg0@[i] == v);
    assert(seq_contains(__arg0@, v));
    if seq_contains(__arg1@, v) {
        let j = choose|j: int| 0 <= j < __arg1@.len() && __arg1@[j] == v;
        assert(__arg1@.contains(v));
    }
    assert(!seq_contains(__arg1@, v));
    assert(seq_contains(__ret0@, v));
    let k = choose|k: int| 0 <= k < __ret0@.len() && __ret0@[k] == v;
    assert(__ret0@.contains(v));
}
