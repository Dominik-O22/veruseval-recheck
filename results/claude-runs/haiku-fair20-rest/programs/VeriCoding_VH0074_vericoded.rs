use vstd::prelude::*;

verus! {

spec fn count_mismatches(s: Seq<i8>, k: int) -> int
    recommends
        0 <= k <= s.len(),
    decreases k
{
    if k <= 0 {
        0
    } else {
        count_mismatches(s, k - 1) + if s[k - 1] != s[s.len() - k] { 1int } else { 0int }
    }
}

fn smallest_change(arr: Vec<i8>) -> (changes: usize)
    ensures
        changes as int == count_mismatches(arr@, arr.len() as int / 2),
        changes <= arr.len() / 2,
{
    let n = arr.len();
    let mut i: usize = 0;
    let mut changes: usize = 0;
    while i < n / 2
        invariant
            n == arr.len(),
            i <= n / 2,
            changes <= i,
            changes as int == count_mismatches(arr@, i as int),
        decreases
            n / 2 - i,
    {
        proof {
            reveal_with_fuel(count_mismatches, 2);
        }
        if arr[i] != arr[n - 1 - i] {
            changes = changes + 1;
        }
        i = i + 1;
    }
    changes
}

fn main() {}

} // verus!