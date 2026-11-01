use vstd::prelude::*;

verus! {

fn target(x: f32) -> (r: f32)
    ensures
        true,
{ x }

} // verus!

fn main() {}
