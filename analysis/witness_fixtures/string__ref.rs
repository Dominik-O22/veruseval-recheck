use vstd::prelude::*;

verus! {

fn target(s: String) -> (r: usize)
    ensures
        r <= s@.len(),
{ 0 }

} // verus!

fn main() {}
