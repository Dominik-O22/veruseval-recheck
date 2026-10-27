use vstd::prelude::*;
verus! {
fn count(n: u32) -> (r: u32)
    ensures r == n
{
    let mut i: u32 = 0;
    while i < n
        invariant i <= n, i >= 0,
        decreases n - i,
    {
        i += 1;
    }
    i
}
fn main() {}
}
