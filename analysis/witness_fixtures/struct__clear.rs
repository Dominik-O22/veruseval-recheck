use vstd::prelude::*;

verus! {

pub struct Point { pub x: i32, pub y: i32 }

fn target(p: Point) -> (r: i32)
    requires
        p.x > -1,
        p.y < 10,
    ensures
        r == p.x,
{ p.x }

} // verus!

fn main() {}
