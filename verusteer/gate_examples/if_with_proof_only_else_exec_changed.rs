use vstd::prelude::*;
verus! {
fn f(a: u32) -> (r: u32)
    ensures r >= a,
{
    let mut x = a;
    if x < 10 {
        x = 0;
    } else {
        proof { assert(x >= 10); }
    }
    x
}
fn main() {}
}
