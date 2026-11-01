// ---- body
match __arg0 {
    Exp::Plus(e1, e2) => { optimize_plus_correct(e1, e2, __arg1); },
    Exp::Mult(e1, e2) => { optimize_mult_correct(e1, e2, __arg1); },
    _ => {},
}
