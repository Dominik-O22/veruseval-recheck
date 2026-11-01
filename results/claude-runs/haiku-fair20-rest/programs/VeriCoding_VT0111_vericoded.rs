// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn infinity_f32() -> (r: f32)
    ensures
        r == 1.0e39f32,
// </vc-spec>
// <vc-code>
{
    1.0e39f32
}
// </vc-code>

// <vc-spec>
fn inf() -> (result: f32)
    ensures
        result == 1.0e39f32,
// </vc-spec>
// <vc-code>
{
    let result: f32 = infinity_f32();
    result
}
// </vc-code>

}
fn main() {}