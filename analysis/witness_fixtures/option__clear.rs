use vstd::prelude::*;

verus! {

fn target(o: Option<u32>) -> (r: u32)
    ensures
        o is None ==> r == 0,
        r <= 4,
{ 0 }

} // verus!

fn main() {}
