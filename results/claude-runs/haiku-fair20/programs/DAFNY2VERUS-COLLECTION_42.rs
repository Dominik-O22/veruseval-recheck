use vstd::prelude::*;
use vstd::seq::*;

verus! {

fn reverse(a: Vec<char>) -> (b: Vec<char>)
    ensures
        b@.len() == a@.len(),
        forall|k: int| 0 <= k < a@.len() ==> #[trigger] b@[k] == a@[a@.len() - 1 - k],
{
    let mut b: Vec<char> = Vec::new();
    let mut k: usize = 0;

    while k < a.len()
        invariant
            0 <= k && k <= a@.len(),
            b@.len() == k,
            forall|j: int| 0 <= j < k as int ==> #[trigger] b@[j] == a@[a@.len() - 1 - j],
        decreases
            a@.len() - k
    {
        b.push(a[a.len() - 1 - k]);
        k = k + 1;
    }

    b
}

}

fn main() {
    let mut a = vec!['d', 'e', 's', 'r', 'e', 'v', 'e', 'r'];
    let b = reverse(a);
    assert_eq!(b.as_slice(), &['r', 'e', 'v', 'e', 'r', 's', 'e', 'd']);
    print!("{:?}", b);
    a = vec!['!'];
    let b = reverse(a);
    assert_eq!(b.as_slice(), &['!']);
    println!("{:?}", b);
}