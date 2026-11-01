// ---- body
let n = __arg0 as int;
if __ret0 {
    assert forall|k: int| 2 <= k < n implies #[trigger] (n % k) != 0 by {
        assert((k as i8) as int == k);
        assert((__arg0 % (k as i8)) != 0);
    }
} else if __arg0 >= 2 {
    let i = choose|i: int| !(2 <= i < __arg0 ==> #[trigger] (__arg0 % (i as i8)) != 0);
    assert((i as i8) as int == i);
    assert(n % i == 0);
}
