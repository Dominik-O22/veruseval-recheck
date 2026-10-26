// <vc-preamble>
use vstd::prelude::*;

verus! {

spec fn h_value(x: int, y: int) -> int {
    x * x + 2 * x * y + x + 1
}

spec fn valid_input(r: int) -> bool {
    r >= 1
}
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn solve(r: i8) -> (result: Vec<i8>)
    requires valid_input(r as int)
    ensures
        (r as int > 4 && (r as int) % 2 == 1) ==> (
            result@.len() == 2
            && result@[0] as int == 1
            && result@[1] as int == ((r as int) - 3) / 2
            && result@[1] as int > 0
            && h_value(result@[0] as int, result@[1] as int) == r as int
        ),
        !(r as int > 4 && (r as int) % 2 == 1) ==> result@.len() == 0
// </vc-spec>
// <vc-code>
{
    if r > 4 && r % 2 == 1 {
        let y: i8 = (r - 3) / 2;
        proof {
            assert((r as int) % 2 == 1);
            assert(y as int == ((r as int) - 3) / 2);
            assert(2 * (y as int) + 3 == r as int);
            assert(y as int > 0);
            assert(h_value(1int, y as int) == 2 * (y as int) + 3);
        }
        let mut v: Vec<i8> = Vec::new();
        v.push(1i8);
        v.push(y);
        proof {
            assert(v@.len() == 2);
            assert(v@[0] == 1i8);
            assert(v@[1] == y);
        }
        v
    } else {
        Vec::new()
    }
}
// </vc-code>

}

fn main() {}