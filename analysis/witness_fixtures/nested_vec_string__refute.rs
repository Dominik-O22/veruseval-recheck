use vstd::prelude::*;

verus! {

fn target(v: Vec<String>) -> (r: usize)
    requires
        v.len() >= 1,
        v[0]@.len() > 0,
    ensures
        r == 0,
{ 0 }

} // verus!

fn main() {}
