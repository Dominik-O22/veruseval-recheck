use vstd::prelude::*;

verus! {

fn target(a: [i32; 3]) -> (r: i32)
    requires
        a[0] >= -1,
    ensures
        r == a[0],
{ a[0] }

} // verus!

fn main() {}
