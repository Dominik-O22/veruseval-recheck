use vstd::prelude::*;

verus! {

fn find_negative_numbers(arr: &Vec<i32>) -> (negative_list: Vec<i32>)
    ensures
        negative_list@ == arr@.filter(|x: i32| x < 0),
{
    let mut negative_list: Vec<i32> = Vec::new();
    let input_len = arr.len();
    let mut index = 0;

    reveal(Seq::filter);
    assert(arr@.take(0int) =~= Seq::<i32>::empty());

    while index < arr.len()
        invariant
            0 <= index <= arr.len(),
            input_len == arr.len(),
            negative_list@ == arr@.take(index as int).filter(|x: i32| x < 0),
        decreases
            arr.len() - index
    {
        reveal(Seq::filter);
        assert(arr@.take(index as int + 1).drop_last() =~= arr@.take(index as int));
        if (arr[index] < 0) {
            negative_list.push(arr[index]);
        }
        index += 1;
    }
    assert(index as int == arr@.len());
    assert(arr@ =~= arr@.take(input_len as int));
    negative_list
}

fn main() {}

} // verus!