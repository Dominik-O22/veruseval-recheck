use vstd::prelude::*;

verus! {

fn target(c: char) -> (r: bool)
    ensures
        r ==> c != 'z',
{ c == 'a' }

} // verus!

fn main() {}
