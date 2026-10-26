use vstd::prelude::*;

verus! {

#[verifier::memoize]
spec fn spec_fib(n: nat) -> nat
    decreases n,
{
    if (n == 0) {
        0
    } else if (n == 1) {
        1
    } else {
        spec_fib((n - 1) as nat) + spec_fib((n - 2) as nat)
    }
}

proof fn lemma_fib_step(m: nat)
    requires
        m >= 2,
    ensures
        spec_fib(m) == spec_fib((m - 1) as nat) + spec_fib((m - 2) as nat),
{
    reveal_with_fuel(spec_fib, 2);
}

proof fn lemma_fib_step_mono(k: nat)
    ensures
        spec_fib(k) <= spec_fib((k + 1) as nat),
{
    reveal_with_fuel(spec_fib, 2);
}

proof fn lemma_fib_monotonic(i: nat, j: nat)
    requires
        i <= j,
    ensures
        spec_fib(i) <= spec_fib(j),
    decreases j - i,
{
    if i == j {
    } else {
        lemma_fib_step_mono((j - 1) as nat);
        lemma_fib_monotonic(i, (j - 1) as nat);
    }
}

fn fib(n: u32) -> (ret: Option<u32>)
    ensures
        match ret {
            None => spec_fib(n as nat) > u32::MAX,
            Some(f) => f == spec_fib(n as nat),
        },
{
    if n == 0 {
        return Some(0);
    }
    if n == 1 {
        return Some(1);
    }
    if n > 47 {
        proof {
            assert(spec_fib(48) > u32::MAX) by (compute_only);
            lemma_fib_monotonic(48, n as nat);
        }
        return None;
    }
    let mut a: u32 = 0;
    let mut b: u32 = 1;
    let mut i: u32 = 1;
    proof {
        assert(spec_fib(0) == 0);
        assert(spec_fib(1) == 1);
        assert(spec_fib(47) < u32::MAX) by (compute_only);
    }
    while i < n
        invariant
            2 <= n <= 47,
            1 <= i <= n,
            a == spec_fib((i - 1) as nat),
            b == spec_fib(i as nat),
        decreases n - i,
    {
        proof {
            assert((i as nat) + 1 <= 47);
            lemma_fib_step((i as nat) + 1);
            lemma_fib_monotonic((i as nat) + 1, 47);
            assert(spec_fib(47) < u32::MAX) by (compute_only);
            assert(spec_fib(((i as nat) + 1) as nat) == spec_fib((i as nat)) + spec_fib(((i as nat) - 1) as nat));
            assert((a as nat) + (b as nat) == spec_fib(((i as nat) + 1) as nat));
            assert((a as nat) + (b as nat) < (u32::MAX as nat));
        }
        let sum = a + b;
        proof {
            assert(sum as nat == spec_fib(((i as nat) + 1) as nat));
        }
        a = b;
        b = sum;
        proof {
            assert(b as nat == spec_fib(((i as nat) + 1) as nat));
        }
        i = i + 1;
    }
    Some(b)
}

} // verus!

fn main() {}