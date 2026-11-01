use vstd::prelude::*;

verus! {

fn target(a: &Vec<u64>) -> (r: bool)
    requires
        a.len() <= usize::MAX,
    ensures
        r,
{ true }

} // verus!

fn main() {}
