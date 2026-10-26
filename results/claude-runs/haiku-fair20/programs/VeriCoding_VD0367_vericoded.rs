use vstd::prelude::*;

verus! {

// <vc-spec>
fn yarra(arr: &Vec<char>) -> (outarr: Vec<char>)
    ensures
        outarr.len() == arr.len(),
        forall|k: int| 0 <= k < arr.len() ==> #[trigger] outarr@[k] == arr@[arr.len() - 1 - k],
// </vc-spec>
// <vc-code>
{
    let len = arr.len();
    let mut outarr = Vec::new();
    let mut i: usize = 0;

    while i < len
        invariant
            len == arr.len(),
            i <= len,
            outarr.len() == i,
            forall|k: int| 0 <= k < i ==> #[trigger] outarr@[k] == arr@[arr.len() - 1 - k],
        decreases len - i
    {
        outarr.push(arr[len - 1 - i]);
        i = i + 1;
    }

    outarr
}
// </vc-code>

fn main() {}

}