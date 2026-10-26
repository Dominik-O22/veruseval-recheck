// <vc-preamble>
use vstd::prelude::*;

verus! {

spec fn valid_input(n: int, m: int) -> bool {
    n >= 1 && m >= 1
}

spec fn min_int(n: int, m: int) -> int {
    if n < m { n } else { m }
}

spec fn expected_odd_min(n: int, m: int) -> bool {
    min_int(n, m) % 2 == 1
}
// </vc-preamble>

// <vc-helpers>
proof fn lemma_min_matches(n: i8, m: i8)
    ensures
        (if n < m { n } else { m }) as int == min_int(n as int, m as int),
{
}
// </vc-helpers>

// <vc-spec>
fn solve(n: i8, m: i8) -> (result: bool)
    requires
        valid_input(n as int, m as int)
    ensures
        result == expected_odd_min(n as int, m as int)
// </vc-spec>
// <vc-code>
{
    let min_val = if n < m { n } else { m };
    proof {
        lemma_min_matches(n, m);
        assert(min_val as int == min_int(n as int, m as int));
        assert(min_val as int >= 1);
        assert((min_val % 2) == 1 <==> (min_val as int) % 2 == 1);
    }
    (min_val % 2) == 1
}
// </vc-code>


}

fn main() {}