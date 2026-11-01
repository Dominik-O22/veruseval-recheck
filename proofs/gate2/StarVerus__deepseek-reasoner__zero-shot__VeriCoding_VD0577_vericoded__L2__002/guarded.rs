// ---- body
let s = __arg0@ + __arg1@;
assert forall|k: int| 0 <= k < __ret0@.len() implies #[trigger] __ret0@[k] == s[k] by {
    if k < __arg0@.len() {
        assert(__ret0@[k] == __arg0@[k]);
    } else {
        let i = k - __arg0@.len();
        assert(__ret0@[__arg0@.len() + i] == __arg1@[i]);
    }
}
assert(__ret0@ =~= s);
