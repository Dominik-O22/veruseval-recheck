use vstd::prelude::*;
use vstd::vec::*;
verus! {
fn first(v: &Vec<u32>) -> (r: u32)
    requires v.len() > 0,
    ensures r == v[0],
{
    v[0]
}
fn main() {}
}
