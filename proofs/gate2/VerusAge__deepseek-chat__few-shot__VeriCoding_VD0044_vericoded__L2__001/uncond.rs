// ---- body
let s = __arg0@ + seq![__arg1];
assert forall|i: int| 0 <= i < __ret0@.len() implies __ret0@[i] == s[i] by {
    if i < __arg0.len() {
        assert(__ret0[i] == __arg0[i]);
    }
}
assert(__ret0@ =~= s);
