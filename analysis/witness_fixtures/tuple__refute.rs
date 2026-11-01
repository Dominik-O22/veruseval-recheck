use vstd::prelude::*;

verus! {

fn target(t: (i32, bool)) -> (r: (i32, bool))
    ensures
        r.0 == t.0,
{ t }

} // verus!

fn main() {}
