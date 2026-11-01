use vstd::prelude::*;

verus! {

fn target(t: (i32, bool)) -> (r: (i32, bool))
    ensures
        r == t,
{ t }

} // verus!

fn main() {}
