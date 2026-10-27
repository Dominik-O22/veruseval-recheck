use vstd::prelude::*;
verus! {
fn count(n: u32) -> (r: u32)
    ensures r == n
{
    let mut i: u32 = 0;
    while i < n
        invariant i <= n,
        decreases n - i,
    {
        i += 1;
    }
    i
}
proof fn helper() {}
fn main() {}
}
