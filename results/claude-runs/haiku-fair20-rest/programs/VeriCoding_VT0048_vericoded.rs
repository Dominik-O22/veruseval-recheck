// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn copyto<T: Copy>(dst: Vec<T>, src: Vec<T>, mask: Vec<bool>) -> (result: Vec<T>)
    requires
        src.len() == dst.len(),
        mask.len() == dst.len(),
    ensures
        result.len() == dst.len(),
        forall|j: int| 0 <= j < dst.len() ==> (mask@[j] ==> #[trigger] result@[j] == src@[j]),
        forall|j: int| 0 <= j < dst.len() ==> (!mask@[j] ==> #[trigger] result@[j] == dst@[j]),
// </vc-spec>
// <vc-code>
{
    let ghost dst_init = dst@;
    let mut result = dst;
    let mut i = 0;
    while i < result.len()
        invariant
            i <= result@.len(),
            result@.len() == dst_init.len(),
            src@.len() == dst_init.len(),
            mask@.len() == dst_init.len(),
            forall|j: int| 0 <= j < (i as int) ==> (mask@[j] ==> #[trigger] result@[j] == src@[j]),
            forall|j: int| 0 <= j < (i as int) ==> (!mask@[j] ==> #[trigger] result@[j] == dst_init[j]),
            forall|j: int| (i as int) <= j < result@.len() ==> #[trigger] result@[j] == dst_init[j],
        decreases result.len() - i
    {
        if mask[i] {
            result.set(i, src[i]);
        }
        i += 1;
    }
    result
}
// </vc-code>

}
fn main() {}