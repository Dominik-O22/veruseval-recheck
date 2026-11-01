use vstd::prelude::*;

verus! {

fn target(a: &Vec<u64>) -> (r: bool)
    ensures
        r,
{ true }

} // verus!

fn main() {}
