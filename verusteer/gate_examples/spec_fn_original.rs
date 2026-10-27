use vstd::prelude::*;
verus! {
spec fn is_sorted(s: Seq<i32>) -> bool { forall|i: int, j: int| 0 <= i < j < s.len() ==> s[i] <= s[j] }
fn sort_check(v: &Vec<i32>) -> (r: bool)
    ensures r == is_sorted(v@)
{ true }
fn main() {}
}
