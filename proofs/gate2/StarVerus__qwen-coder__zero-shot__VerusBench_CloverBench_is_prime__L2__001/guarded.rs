// ---- body
let c = __arg0;
if __ret0 {
    assert forall|f: nat| 1 < f && f < c as nat implies !divides(f, c as nat) by {
        let g = f as u64;
        assert(g as nat == f);
        assert(2 <= g < c);
        assert((c % g) != 0);
        assert((c as nat) % f == (c % g) as nat);
    }
    assert(is_prime(c as nat));
} else {
    let g = choose|g: u64| !(2 <= g < c ==> #[trigger] (c % g) != 0);
    assert(2 <= g < c && c % g == 0);
    let f = g as nat;
    assert((c as nat) % f == (c % g) as nat);
    assert(divides(f, c as nat));
    assert(!is_prime(c as nat));
}
