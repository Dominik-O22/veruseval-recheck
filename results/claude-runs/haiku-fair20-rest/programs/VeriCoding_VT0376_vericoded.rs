// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
struct ChebyshevPoly {
    coef: Vec<i32>,
    domain_min: i32,
    domain_max: i32,
    window_min: i32,
    window_max: i32,
}

fn chebyshev(coef: Vec<i8>) -> (result: ChebyshevPoly)
    ensures
        result.coef@.len() == coef@.len(),
        forall|j: int| 0 <= j < coef@.len() ==> result.coef@[j] == (coef@[j] as i32),
        result.domain_min == -1,
        result.domain_max == 1,
        result.window_min == -1,
        result.window_max == 1,
// </vc-spec>
// <vc-code>
{
    let mut result_coef: Vec<i32> = Vec::new();
    let mut i: usize = 0;
    while i < coef.len()
        invariant
            i <= coef.len(),
            result_coef@.len() == i,
            forall|j: int| 0 <= j < i ==> result_coef@[j] == (coef@[j] as i32),
        decreases coef.len() - i,
    {
        result_coef.push(coef[i] as i32);
        i = i + 1;
    }
    ChebyshevPoly {
        coef: result_coef,
        domain_min: -1,
        domain_max: 1,
        window_min: -1,
        window_max: 1,
    }
}
// </vc-code>

}
fn main() {}