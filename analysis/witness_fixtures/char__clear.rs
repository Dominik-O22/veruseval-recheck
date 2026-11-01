use vstd::prelude::*;

verus! {

fn target(c: char) -> (r: bool)
    ensures
        r == (c == 'a'),
        r ==> c != 'b',
{ c == 'a' }

} // verus!

fn main() {}
