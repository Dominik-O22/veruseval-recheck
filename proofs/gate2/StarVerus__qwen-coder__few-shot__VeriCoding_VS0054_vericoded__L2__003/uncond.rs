// ---- body
let a = __arg0;
let r = __ret0;
if r.len() > 0 {
    assert(r[0].len() == a.len());
    if a.len() > 0 {
        assert(matrix_cols(a) == r.len());
        assert(matrix_cols(r) == a.len());
        assert(matrix_size(r) == r.len() * a.len());
        assert(r.len() as int * a.len() as int == a.len() as int * r.len() as int) by (nonlinear_arith);
    } else {
        assert(matrix_cols(r) == 0);
        assert(matrix_size(r) == 0);
        assert(matrix_rows(a) == 0);
        assert(matrix_cols(a) * matrix_rows(a) == 0);
    }
} else {
    assert(matrix_size(r) == 0);
    if a.len() > 0 {
        assert(matrix_cols(a) == 0);
    }
    assert(matrix_cols(a) * matrix_rows(a) == 0);
}
