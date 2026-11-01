// ---- body
assert forall|i: int| 0 <= i < __arg0@.len() implies #[trigger] __ret0.0@[i][0] == __arg0@[i] by {
    assert(__ret0.0@[i]@.len() == 1);
    assert(__ret0.0@[i]@[0] == __arg0@[i]);
}
