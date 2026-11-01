use vstd::prelude::*;

verus! {

fn find_first_odd(arr: &Vec<u32>) -> (index: Option<usize>)
    ensures
        match index {
            Some(idx) => {
                &&& idx < arr.len()
                &&& arr[idx as int] % 2 != 0
                &&& forall|k: int| 0 <= k < idx as int ==> arr[k] % 2 == 0
            },
            None => forall|k: int| 0 <= k < arr.len() ==> arr[k] % 2 == 0,
        },
{
    let input_len = arr.len();
    let mut index = 0;
    while index < arr.len()
        invariant
            0 <= index <= arr.len(),
            forall|k: int| 0 <= k < index as int ==> arr[k] % 2 == 0,
        decreases
            arr.len() - index
    {
        if (arr[index] % 2 != 0) {
            return Some(index);
        }
        index += 1;
    }
    None
}

fn main() {}

} // verus!