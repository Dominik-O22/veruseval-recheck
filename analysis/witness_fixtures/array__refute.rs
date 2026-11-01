use vstd::prelude::*;

verus! {

fn target(a: [i32; 3]) -> (r: i32)
    requires
        a[0] > 0,
    ensures
        r == a[0],
{ a[0] }

} // verus!

fn main() {}
