// ---- body
assert forall|i: int, j: int| 0 <= i < __arg1.len() && 0 <= j < __arg0.len() implies
    #[trigger] __ret0.0[i][j] == __arg0[j] by {
    let a = __ret0.0[i][j];
    let b = __ret0.1[i][j];
    assert(__ret0.0[i][j] == __arg0[j] && __ret0.1[i][j] == __arg1[i]);
}
