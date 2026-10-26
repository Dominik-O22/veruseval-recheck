// <vc-preamble>
use vstd::prelude::*;

verus! {

spec fn expected_output(temp: int) -> Seq<u8> {
    if temp >= 30 {
        seq![89u8, 101u8, 115u8, 10u8]
    } else {
        seq![78u8, 111u8, 10u8]
    }
}
// </vc-preamble>

// <vc-helpers>
// </vc-helpers>

// <vc-spec>
fn build_output_vec(temp: i8) -> (v: Vec<u8>)
    ensures
        v@ == expected_output(temp as int),
// </vc-spec>
// <vc-code>
{
    if temp >= 30 {
        let v1: Vec<u8> = vec![89u8, 101u8, 115u8, 10u8];
        assert(v1@ == seq![89u8, 101u8, 115u8, 10u8]);
        v1
    } else {
        let v2: Vec<u8> = vec![78u8, 111u8, 10u8];
        assert(v2@ == seq![78u8, 111u8, 10u8]);
        v2
    }
}
// </vc-code>

// <vc-spec>
fn solve(x: i8) -> (result: Vec<u8>)
    ensures
        result@ == expected_output(x as int),
// </vc-spec>
// <vc-code>
{
    let result = build_output_vec(x);
    result
}
// </vc-code>

}

fn main() {}