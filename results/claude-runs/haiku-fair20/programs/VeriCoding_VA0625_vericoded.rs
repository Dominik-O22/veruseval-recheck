// <vc-preamble>
use vstd::prelude::*;

verus! {
spec fn is_delicious(a: int, b: int) -> bool {
    b - a <= 0
}

spec fn is_safe(x: int, a: int, b: int) -> bool {
    0 < b - a && b - a <= x
}

spec fn is_dangerous(x: int, a: int, b: int) -> bool {
    b - a > 0 && b - a > x
}
// </vc-preamble>

// <vc-helpers>
// </vc-helpers>

// <vc-spec>
fn determine_food_safety(x: i8, a: i8, b: i8) -> (outcome: &'static str)
    ensures
        outcome == "delicious" <==> is_delicious(a as int, b as int),
        outcome == "safe" <==> is_safe(x as int, a as int, b as int),
        outcome == "dangerous" <==> is_dangerous(x as int, a as int, b as int),
        outcome == "delicious" || outcome == "safe" || outcome == "dangerous",
// </vc-spec>
// <vc-code>
{
    let days_rt: i32 = (b as i32) - (a as i32);
    proof {
        assert(days_rt as int == b as int - a as int);
    }
    let res: &'static str;
    if days_rt <= 0 {
        res = "delicious";
    } else if days_rt <= x as i32 {
        res = "safe";
    } else {
        res = "dangerous";
    }
    res
}
// </vc-code>


}

fn main() {}