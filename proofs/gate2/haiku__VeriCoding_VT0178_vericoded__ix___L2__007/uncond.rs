// ---- body
assert forall|i: int| 0 <= i < __arg0@.len() implies #[trigger] __ret0.0@[i][0] == __arg0@[i] by {
    assert(__ret0.0@[i]@.len() == 1);
}
assert forall|j: int| 0 <= j < __arg1@.len() implies #[trigger] __ret0.1@[0][j] == __arg1@[j] by {
    assert(__ret0.1@[0]@ == __arg1@);
}
assert forall|i: int, j: int| 0 <= i < __arg0@.len() && 0 <= j < __arg1@.len() implies
            __ret0.0@[i][0] == __arg0@[i] && __ret0.1@[0][j] == __arg1@[j] by {
    assert(__ret0.0@[i][0] == __arg0@[i]);
    assert(__ret0.1@[0][j] == __arg1@[j]);
}
