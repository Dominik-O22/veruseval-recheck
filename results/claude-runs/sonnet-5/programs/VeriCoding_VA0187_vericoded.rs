// <vc-preamble>
use vstd::prelude::*;

verus! {

spec fn valid_input(n: int, m: int) -> bool {
    n >= 1 && m >= 1
}

spec fn min_spec(n: int, m: int) -> int {
    if n < m { n } else { m }
}

spec fn first_player_wins(n: int, m: int) -> bool {
    min_spec(n, m) % 2 == 1
}
// </vc-preamble>

// <vc-helpers>
proof fn lemma_min_positive(n: int, m: int)
    requires
        valid_input(n, m),
    ensures
        min_spec(n, m) >= 1,
        min_spec(n, m) <= n,
        min_spec(n, m) <= m,
{
}
// </vc-helpers>

// <vc-spec>
fn solve(n: i8, m: i8) -> (result: bool)
    requires
        valid_input(n as int, m as int),
    ensures
        result == first_player_wins(n as int, m as int),
        result == (min_spec(n as int, m as int) % 2 == 1),
// </vc-spec>
// <vc-code>
{
    let min_val = if n < m { n } else { m };
    proof {
        lemma_min_positive(n as int, m as int);
        assert(min_val as int == min_spec(n as int, m as int));
        assert(min_val >= 1);
    }
    (min_val % 2) == 1
}
// </vc-code>

}

fn main() {}