use vstd::prelude::*;

verus! {

fn target(s: &str) -> (r: bool)
    ensures
        r == (s@.len() > 0 && s@[0] == 'a'),
{ true }

} // verus!

fn main() {}
