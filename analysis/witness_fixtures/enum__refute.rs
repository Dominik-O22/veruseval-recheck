use vstd::prelude::*;

verus! {

pub enum Color { Red, Green, Blue }

fn target(c: Color) -> (r: u8)
    ensures
        r <= 2,
{ 0 }

} // verus!

fn main() {}
