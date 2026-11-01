proof fn lemma_ve_all(e: Exp)
    ensures valid_exp(e)
    decreases e
{
    match e {
        Exp::Plus(a, b) => { lemma_ve_all(*a); lemma_ve_all(*b); },
        Exp::Mult(a, b) => { lemma_ve_all(*a); lemma_ve_all(*b); },
        _ => {},
    }
}
// ---- body
lemma_ve_all(__arg0);
