use vstd::prelude::*;

verus! {

fn target(x: f32) -> (r: f32)
    ensures
        r == x,
        x == x,
{ x }

} // verus!

fn main() {}
