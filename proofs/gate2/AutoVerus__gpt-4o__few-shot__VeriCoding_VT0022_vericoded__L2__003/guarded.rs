// ---- body
assert forall|i: int, j: int| 0 <= i < __arg0 && 0 <= j < __arg0 implies
    __ret0[i][j] == (if i == j { 1.0f64 } else { 0.0f64 }) by {
    assert(__ret0[i][j] == diag_val_spec(i, j));
}
