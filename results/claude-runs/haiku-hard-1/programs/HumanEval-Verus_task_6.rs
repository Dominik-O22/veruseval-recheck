// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>
spec fn prefix_sum(s: Seq<i32>) -> int
    decreases s.len(),
{
    if s.len() == 0 {
        0
    } else {
        prefix_sum(s.drop_last()) + s.last() as int
    }
}

proof fn lemma_prefix_empty(s: Seq<i32>)
    requires
        s.len() == 0,
    ensures
        prefix_sum(s) == 0,
{
}

proof fn lemma_prefix_step(s: Seq<i32>, i: int)
    requires
        0 < i <= s.len(),
    ensures
        prefix_sum(s.subrange(0, i)) == prefix_sum(s.subrange(0, i - 1)) + s[i - 1] as int,
{
    let t = s.subrange(0, i);
    assert(t.drop_last() =~= s.subrange(0, i - 1));
    assert(t.last() == s[i - 1]);
}
// </vc-helpers>

// <vc-spec>
fn below_zero(operations: Vec<i32>) -> (result: bool)
    ensures
        result <==> exists|i: int|
            0 <= i <= operations@.len() && #[trigger] prefix_sum(operations@.subrange(0, i)) < 0,
// </vc-spec>
// <vc-code>
{
    let mut s = 0i32;
    let mut num_overflows: usize = 0;
    proof {
        lemma_prefix_empty(operations@.subrange(0, 0));
    }
    for k in 0..operations.len()
        invariant
            0 <= k <= operations.len(),
            0 <= s <= i32::MAX,
            0 <= num_overflows <= k,
            s as int + (num_overflows as int) * 2147483648 == prefix_sum(
                operations@.subrange(0, k as int),
            ),
            forall|j: int| 0 <= j <= k as int ==> #[trigger] prefix_sum(operations@.subrange(0, j)) >= 0,
    {
        proof {
            lemma_prefix_step(operations@, k as int + 1);
        }
        let op = operations[k];
        if op >= 0 {
            if s > i32::MAX - op {
                s += op - i32::MAX - 1;
                num_overflows += 1;
            } else {
                s += op;
            }
        } else {
            s += op;
            if s < 0 {
                if num_overflows == 0 {
                    proof {
                        assert(0 <= k as int + 1 <= operations@.len());
                        assert(prefix_sum(operations@.subrange(0, k as int + 1)) < 0);
                        assert(exists|i: int|
                            0 <= i <= operations@.len() && #[trigger] prefix_sum(operations@.subrange(0, i)) < 0
                        ) by {
                            assert(0 <= k as int + 1 <= operations@.len()
                                && prefix_sum(operations@.subrange(0, k as int + 1)) < 0);
                        };
                    }
                    return true;
                }
                num_overflows -= 1;
                s = s + i32::MAX + 1;
            }
        }
    }
    false
}
// </vc-code>

}

fn main() {}