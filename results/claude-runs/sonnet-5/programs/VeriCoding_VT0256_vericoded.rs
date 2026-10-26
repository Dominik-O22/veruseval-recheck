// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn bitwise_and(x1: &Vec<u8>, x2: &Vec<u8>) -> (result: Vec<u8>)
    requires
        x1.len() == x2.len(),
    ensures
        result.len() == x1.len(),
        forall|i: int| 0 <= i < result.len() ==> result[i] == (x1[i] & x2[i]),
// </vc-spec>
// <vc-code>
{
    let mut result: Vec<u8> = Vec::new();
    let mut i: usize = 0;
    while i < x1.len()
        invariant
            0 <= i <= x1.len(),
            x1.len() == x2.len(),
            result.len() == i,
            forall|j: int| 0 <= j < (i as int) ==> result[j] == (x1[j] & x2[j]),
        decreases x1.len() - i
    {
        let b1 = x1[i];
        let b2 = x2[i];
        let r = b1 & b2;
        result.push(r);
        i = i + 1;
    }
    result
}
// </vc-code>

}
fn main() {}