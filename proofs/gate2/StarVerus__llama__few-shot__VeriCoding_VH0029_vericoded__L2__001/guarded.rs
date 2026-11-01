// ---- body
let n = __arg0 as int;
if __ret0 {
    assert forall|k: int| 2 <= k < n implies #[trigger] (n % k) != 0 by {
        assert(!is_divisible(n, k));
    }
} else {
    let k = choose|k: int| !(2 <= k < n ==> !is_divisible(n, k));
    assert(n % k == 0);
}
