// Proves the reference contract and Haiku's contract for HumanEval-Verus_task_6
// (below_zero) are equivalent: both postconditions sum the same prefix.
use vstd::prelude::*;
verus! {

// Reference definitions (front-recursive sum over an int sequence).
pub open spec fn sum(s: Seq<int>) -> int
    decreases s.len(),
{
    if s.len() == 0 { 0 } else { s[0] + sum(s.skip(1)) }
}

pub open spec fn first_n(s: Seq<i32>, n: int) -> Seq<int> {
    s.take(n).map(|_idx, j: i32| j as int)
}

// Haiku's definition (back-recursive sum over an i32 sequence).
spec fn prefix_sum(s: Seq<i32>) -> int
    decreases s.len(),
{
    if s.len() == 0 { 0 } else { prefix_sum(s.drop_last()) + s.last() as int }
}

// Front-recursive sum peels off the last element too.
proof fn lemma_sum_drop_last(s: Seq<int>)
    requires s.len() > 0,
    ensures sum(s) == sum(s.drop_last()) + s.last(),
    decreases s.len(),
{
    reveal_with_fuel(sum, 2);
    if s.len() == 1 {
        assert(s.skip(1).len() == 0);
        assert(s.drop_last().len() == 0);
        assert(sum(s) == s[0] + sum(s.skip(1)));
    } else {
        assert(sum(s) == s[0] + sum(s.skip(1)));
        lemma_sum_drop_last(s.skip(1));
        assert(s.skip(1).drop_last() =~= s.drop_last().skip(1));
        assert(s.skip(1).last() == s.last());
        assert(s.drop_last()[0] == s[0]);
        assert(sum(s.drop_last()) == s.drop_last()[0] + sum(s.drop_last().skip(1)));
    }
}

proof fn lemma_same_sum(s: Seq<i32>)
    ensures prefix_sum(s) == sum(s.map(|_idx, j: i32| j as int)),
    decreases s.len(),
{
    let m = s.map(|_idx, j: i32| j as int);
    if s.len() > 0 {
        lemma_same_sum(s.drop_last());
        lemma_sum_drop_last(m);
        assert(m.drop_last() =~= s.drop_last().map(|_idx, j: i32| j as int));
    }
}

// The two postconditions agree for every input and every prefix length.
proof fn contracts_equivalent(ops: Seq<i32>, i: int)
    requires 0 <= i <= ops.len(),
    ensures sum(first_n(ops, i)) == prefix_sum(ops.subrange(0, i)),
{
    lemma_same_sum(ops.subrange(0, i));
    assert(ops.take(i) =~= ops.subrange(0, i));
}

fn main() {}
}
