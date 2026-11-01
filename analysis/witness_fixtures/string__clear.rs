use vstd::prelude::*;

verus! {

fn target(s: String) -> (r: usize)
    ensures
        r == 0,
{ 0 }

} // verus!

fn main() {}
