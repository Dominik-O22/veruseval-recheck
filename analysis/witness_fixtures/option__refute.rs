use vstd::prelude::*;

verus! {

fn target(o: Option<u32>) -> (r: u32)
    ensures
        r <= 5,
{ 0 }

} // verus!

fn main() {}
