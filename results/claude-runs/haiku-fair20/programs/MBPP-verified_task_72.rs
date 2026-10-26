use vstd::prelude::*;

verus! {

spec fn matches_at(main: Seq<i32>, sub: Seq<i32>, idx: int) -> bool {
    0 <= idx && idx + sub.len() <= main.len() &&
    forall|k: int| 0 <= k < sub.len() ==> main[idx + k] == sub[k]
}

fn sub_array_at_index(main: &Vec<i32>, sub: &Vec<i32>, idx: usize) -> (result: bool)
    requires
        idx as int + sub.len() as int <= main.len() as int,
    ensures
        result == matches_at(main@, sub@, idx as int),
{
    let mut i = 0;
    while i < sub.len()
        invariant
            0 <= i <= sub.len(),
            idx as int + sub.len() as int <= main.len() as int,
            forall|k: int| 0 <= k < i ==> main@[idx as int + k] == sub@[k],
        decreases
            sub.len() - i
    {
        if (main[idx + i] != sub[i]) {
            proof {
                assert(main@[idx as int + i as int] != sub@[i as int]);
                assert(!matches_at(main@, sub@, idx as int));
            }
            return false;
        }
        i += 1;
    }
    proof {
        assert(matches_at(main@, sub@, idx as int));
    }
    true
}

fn is_sub_array(main: &Vec<i32>, sub: &Vec<i32>) -> (result: bool)
    ensures
        result == (exists|k: int|
            0 <= k <= (main.len() as int) - (sub.len() as int) && #[trigger] matches_at(main@, sub@, k)),
{
    if sub.len() > main.len() {
        proof {
            assert(forall|k: int|
                0 <= k <= (main@.len() as int) - (sub@.len() as int) ==> !matches_at(main@, sub@, k));
        }
        return false;
    }
    let mut index = 0;
    while index <= (main.len() - sub.len())
        invariant
            sub.len() <= main.len(),
            0 <= index <= (main.len() as int) - (sub.len() as int) + 1,
            forall|k: int| 0 <= k < index ==> !matches_at(main@, sub@, k),
        decreases
            (main.len() as int) - (sub.len() as int) + 1 - (index as int)
    {
        if (sub_array_at_index(&main, &sub, index)) {
            proof {
                assert(matches_at(main@, sub@, index as int));
            }
            return true;
        }
        proof {
            assert(!matches_at(main@, sub@, index as int));
        }
        index += 1;
    }
    proof {
        assert(forall|k: int|
            0 <= k <= (main@.len() as int) - (sub@.len() as int) ==> !matches_at(main@, sub@, k));
    }
    false
}

} // verus!

fn main() {}