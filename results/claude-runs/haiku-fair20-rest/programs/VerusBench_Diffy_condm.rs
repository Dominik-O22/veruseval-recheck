use vstd::prelude::*;
fn main() {}
verus!{
pub fn myfun(a: &mut Vec<i32>, N: u32)
	requires
		old(a).len() == N as usize,
	ensures
		a.len() == N as usize,
		forall |k:int| 0 <= k < N as int ==> a[k] == (if N % 2 == 0 { 2i32 } else { 1i32 }),
{
	let mut i: usize = 0;

	while (i < N as usize)
		invariant
			i <= N as usize,
			a.len() == N as usize,
			forall |k:int| 0 <= k < i as int ==> a[k] == 0,
		decreases
			(N as usize) - i
	{
		a.set(i, 0);
		i = i + 1;
	}

	i = 0;
	while (i < N as usize)
		invariant
			i <= N as usize,
			a.len() == N as usize,
			forall |k:int| 0 <= k < i as int ==> a[k] == (if N % 2 == 0 { 2i32 } else { 1i32 }),
			forall |k:int| i as int <= k < N as int ==> a[k] == 0,
		decreases
			(N as usize) - i
	{
		proof {
			assert(a[i as int] == 0);
		}
		if (N % 2 == 0) {
			a.set(i, a[i] + 2);
		} else {
			a.set(i, a[i] + 1);
		}
		i = i + 1;
	}
}
}