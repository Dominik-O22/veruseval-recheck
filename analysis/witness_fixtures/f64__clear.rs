use vstd::prelude::*;

verus! {

fn target(v: Vec<f64>) -> (r: usize)
    requires
        v.len() > 0,
    ensures
        r == 0,
{ 0 }

} // verus!

fn main() {}
