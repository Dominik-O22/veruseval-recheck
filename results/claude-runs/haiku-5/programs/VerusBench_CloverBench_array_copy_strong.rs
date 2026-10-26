use vstd::prelude::*;

fn main() {}

verus! {

// <vc-helpers>
// No additional helpers needed for this implementation
// </vc-helpers>

// <vc-spec>
fn copy(a: &Vec<u64>) -> (b: Vec<u64>)
    ensures
        b@.len() == a@.len(),
        forall|i: int| 0 <= i < a@.len() ==> #[trigger] b@[i] == a@[i],
// </vc-spec>
// <vc-code>
{
    let mut b = Vec::with_capacity(a.len());
    let mut n: usize = 0;
    let len: usize = a.len();
    while n != len
        invariant
            len == a.len(),
            n <= len,
            b.len() == n,
            forall|j: int| 0 <= j < n as int ==> #[trigger] b@[j] == a@[j],
        decreases len - n
    {
        b.push(a[n]);
        n = n + 1;
    }
    b
}
// </vc-code>

} // verus!