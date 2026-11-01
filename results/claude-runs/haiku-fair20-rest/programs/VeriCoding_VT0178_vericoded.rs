// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn singleton_vec_i8(x: i8) -> (result: Vec<i8>)
    ensures
        result@.len() == 1,
        result@[0] == x,
// </vc-spec>
// <vc-code>
{
    let mut v: Vec<i8> = Vec::new();
    v.push(x);
    v
}
// </vc-code>

fn copy_vec_i8(src: &Vec<i8>) -> (dest: Vec<i8>)
    ensures
        dest@ == src@,
{
    let mut d: Vec<i8> = Vec::new();
    let mut j: usize = 0;
    while j < src.len()
        invariant
            0 <= j as int <= src@.len(),
            d@ == src@.subrange(0, j as int),
        decreases src.len() - j
    {
        let val = src[j];
        d.push(val);
        proof {
            assert(d@ =~= src@.subrange(0, j as int + 1));
        }
        j += 1;
    }
    d
}

fn ix_(seq1: Vec<i8>, seq2: Vec<i8>) -> (result: (Vec<Vec<i8>>, Vec<Vec<i8>>))
    ensures
        result.0@.len() == seq1@.len() && forall|k: int| 0 <= k < result.0@.len() ==>
            #[trigger] result.0@[k]@.len() == 1 && result.0@[k]@[0] == seq1@[k],
        result.1@.len() == 1 && result.1@[0]@ == seq2@,
{
    let mut rows0: Vec<Vec<i8>> = Vec::new();
    let mut i: usize = 0;
    while i < seq1.len()
        invariant
            0 <= i as int <= seq1@.len(),
            rows0@.len() == i as int,
            forall|k: int| 0 <= k < i as int ==>
                #[trigger] rows0@[k]@.len() == 1 && rows0@[k]@[0] == seq1@[k],
        decreases seq1.len() - i
    {
        let val = seq1[i];
        let single = singleton_vec_i8(val);
        rows0.push(single);
        proof {
            assert(rows0@.len() == i as int + 1);
        }
        i += 1;
    }
    let row = copy_vec_i8(&seq2);
    let mut rows1: Vec<Vec<i8>> = Vec::new();
    let ghost row_view = row@;
    rows1.push(row);
    proof {
        assert(rows1@[0]@ == row_view);
        assert(row_view == seq2@);
    }
    (rows0, rows1)
}
// </vc-code>

}
fn main() {}