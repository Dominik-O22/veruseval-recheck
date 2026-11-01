use vstd::prelude::*;

verus! {

fn target(c: char) -> (r: bool)
    ensures
        r == (c == 'a'),
{ c == 'a' }

} // verus!

fn main() {}
