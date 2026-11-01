// <vc-preamble>
use vstd::prelude::*;

verus! {

struct Laguerre {

    coef: Vec<f32>,

    domain: [f32; 2],

    window: [f32; 2],
}
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn make_unit_interval() -> (result: [f32; 2])
    ensures
        result[0] == 0.0f32,
        result[1] == 1.0f32,
// </vc-spec>
// <vc-code>
{
    [0.0f32, 1.0f32]
}
// </vc-code>

// <vc-spec>
fn assemble_laguerre(coef: Vec<f32>, domain: [f32; 2], window: [f32; 2]) -> (result: Laguerre)
    ensures
        result.coef@ == coef@,
        result.domain == domain,
        result.window == window,
        result.domain[0] == domain[0] && result.domain[1] == domain[1],
        result.window[0] == window[0] && result.window[1] == window[1],
// </vc-spec>
// <vc-code>
{
    Laguerre { coef, domain, window }
}
// </vc-code>

// <vc-spec>
fn make_laguerre(coefficients: Vec<f32>) -> (result: Laguerre)
    ensures
        result.coef@ == coefficients@,
        result.domain[0] == 0.0f32 && result.domain[1] == 1.0f32,
        result.window[0] == 0.0f32 && result.window[1] == 1.0f32,
// </vc-spec>
// <vc-code>
{
    let d = make_unit_interval();
    let w = make_unit_interval();
    let r = assemble_laguerre(coefficients, d, w);
    r
}
// </vc-code>

}
fn main() {}