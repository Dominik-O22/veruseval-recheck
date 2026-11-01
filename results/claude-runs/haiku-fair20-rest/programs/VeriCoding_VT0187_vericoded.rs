// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>
spec fn cyc_idx(mask: Seq<bool>, n: int, len: int) -> int
    decreases n
{
    if n <= 0 {
        0int
    } else {
        if mask[n - 1] {
            if cyc_idx(mask, n - 1, len) + 1 == len { 0int } else { cyc_idx(mask, n - 1, len) + 1 }
        } else {
            cyc_idx(mask, n - 1, len)
        }
    }
}

proof fn lemma_cyc_bounds(mask: Seq<bool>, n: int, len: int)
    requires
        0 <= n,
        len > 0,
    ensures
        0 <= cyc_idx(mask, n, len) < len,
    decreases n
{
    reveal_with_fuel(cyc_idx, 2);
    if n > 0 {
        lemma_cyc_bounds(mask, n - 1, len);
    }
}

proof fn lemma_cyc_step(mask: Seq<bool>, n: int, len: int)
    requires
        0 <= n < mask.len(),
    ensures
        cyc_idx(mask, n + 1, len) == (if mask[n] {
            if cyc_idx(mask, n, len) + 1 == len { 0int } else { cyc_idx(mask, n, len) + 1 }
        } else {
            cyc_idx(mask, n, len)
        }),
{
    reveal_with_fuel(cyc_idx, 2);
}
// </vc-helpers>

// <vc-spec>
fn place(arr: Vec<f32>, mask: Vec<bool>, vals: Vec<f32>) -> (result: Vec<f32>)
    requires
        arr.len() == mask.len(),
        vals.len() > 0,
    ensures
        result.len() == arr.len(),
        forall|i: int| 0 <= i < arr.len() ==> (!mask@[i] ==> result@[i] == arr@[i]),
        forall|i: int| 0 <= i < arr.len() ==> (mask@[i] ==> result@[i] == vals@[cyc_idx(mask@, i, vals.len() as int)]),
// </vc-spec>
// <vc-code>
{
    let mut result = Vec::new();
    let mut val_idx: usize = 0;
    let mut i: usize = 0;
    proof {
        reveal_with_fuel(cyc_idx, 2);
    }
    while i < arr.len()
        invariant
            i <= arr.len(),
            arr.len() == mask.len(),
            vals.len() > 0,
            result.len() == i,
            val_idx < vals.len(),
            val_idx as int == cyc_idx(mask@, i as int, vals.len() as int),
            forall|k: int| 0 <= k < i ==> (!mask@[k] ==> result@[k] == arr@[k]),
            forall|k: int| 0 <= k < i ==> (mask@[k] ==> result@[k] == vals@[cyc_idx(mask@, k, vals.len() as int)]),
        decreases arr.len() - i
    {
        if mask[i] {
            result.push(vals[val_idx]);
            val_idx = if val_idx + 1 == vals.len() { 0 } else { val_idx + 1 };
        } else {
            result.push(arr[i]);
        }
        proof {
            lemma_cyc_step(mask@, i as int, vals.len() as int);
            lemma_cyc_bounds(mask@, i as int + 1, vals.len() as int);
        }
        i = i + 1;
    }
    result
}
// </vc-code>

}
fn main() {}