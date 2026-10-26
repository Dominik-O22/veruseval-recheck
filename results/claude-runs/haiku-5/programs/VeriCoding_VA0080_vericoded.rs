// <vc-preamble>
use vstd::prelude::*;

verus! {
spec fn is_odd_case(r: int) -> bool {
    r > 4 && r % 2 == 1
}

spec fn expected_y(r: int) -> int
    recommends is_odd_case(r)
{
    (r - 3) / 2
}
// </vc-preamble>

// <vc-helpers>
// </vc-helpers>

// <vc-spec>
fn solve(r: i8) -> (result: Vec<i8>)
    ensures
        is_odd_case(r as int) ==> (
            result@.len() == 2 &&
            result@[0] as int == 1 &&
            result@[1] as int == expected_y(r as int)
        ),
        !is_odd_case(r as int) ==> result@.len() == 0
// </vc-spec>
// <vc-code>
{
    if r > 4 && r % 2 == 1 {
        let y: i8 = (r - 3) / 2;
        proof {
            assert(is_odd_case(r as int));
            assert(y as int == (r as int - 3) / 2);
        }
        let mut v: Vec<i8> = Vec::new();
        v.push(1i8);
        v.push(y);
        v
    } else {
        Vec::new()
    }
}
// </vc-code>


}

fn main() {}