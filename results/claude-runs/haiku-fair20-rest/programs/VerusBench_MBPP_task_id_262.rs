// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>

// </vc-helpers>

// <vc-spec>
fn split_array(list: &Vec<i32>, l: usize) -> (new_list: (Vec<i32>, Vec<i32>))

    requires
        l <= list@.len(),

    ensures
        new_list.0@ == list@.subrange(0, l as int),
        new_list.1@ == list@.subrange(l as int, list@.len() as int),
// </vc-spec>
// <vc-code>
{
    let mut part1: Vec<i32> = Vec::new();
    let mut index = 0;
    while index < l
        invariant
            l <= list.len(),
            0 <= index <= l,
            part1@ =~= list@.subrange(0, index as int),
        decreases
            l - index
    {
        part1.push(list[index]);
        index += 1;
    }
    let mut part2: Vec<i32> = Vec::new();
    index = l;
    while index < list.len()
        invariant
            l <= index <= list.len(),
            part2@ =~= list@.subrange(l as int, index as int),
        decreases
            list.len() - index
    {
        part2.push(list[index]);
        index += 1;
    }
    (part1, part2)
}
// </vc-code>

}

fn main() {}