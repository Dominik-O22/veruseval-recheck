use vstd::prelude::*;

verus! {

fn target(s: &str) -> (r: bool)
    ensures
        r ==> s@.len() >= 0,
{ true }

} // verus!

fn main() {}
