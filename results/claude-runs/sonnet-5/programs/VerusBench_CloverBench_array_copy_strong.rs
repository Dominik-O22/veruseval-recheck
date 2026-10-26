use vstd::prelude::*;

fn main() {}
verus! {

fn copy(a: &Vec<u64>) -> (b: Vec<u64>)
    ensures
        b.len() == a.len(),
        forall|i: int| 0 <= i < a.len() ==> b[i] == a[i],
{
    let mut b = Vec::with_capacity(a.len());
    let mut n: usize = 0;
    let len: usize = a.len();
    while n != len
        invariant
            len == a.len(),
            n <= len,
            b.len() == n,
            forall|i: int| 0 <= i < n as int ==> b[i] == a[i],
        decreases len - n
    {
        b.push(a[n]);
        n = n + 1;
    }
    b
}

} // verus!