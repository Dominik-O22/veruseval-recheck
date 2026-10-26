// <vc-preamble>
use vstd::prelude::*;

verus! {

spec fn yes_output() -> Seq<u8> {
    seq![89u8, 101u8, 115u8, 10u8]
}

spec fn no_output() -> Seq<u8> {
    seq![78u8, 111u8, 10u8]
}

spec fn correct_output(temp: int, result: Seq<u8>) -> bool {
    (temp >= 30 ==> result == yes_output()) &&
    (temp < 30 ==> result == no_output())
}
// </vc-preamble>

// <vc-helpers>
fn build_output_vec(temp: i8) -> (v: Vec<u8>)
    ensures
        correct_output(temp as int, v@),
{
    if temp >= 30 {
        let v1: Vec<u8> = vec![89u8, 101u8, 115u8, 10u8];
        assert(v1@ == yes_output());
        v1
    } else {
        let v2: Vec<u8> = vec![78u8, 111u8, 10u8];
        assert(v2@ == no_output());
        v2
    }
}
// </vc-helpers>

// <vc-spec>
fn solve(x: i8) -> (result: Vec<u8>)
    ensures correct_output(x as int, result@)
// </vc-spec>
// <vc-code>
{
    let result = build_output_vec(x);
    result
}
// </vc-code>

}
fn main() {}