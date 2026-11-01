// ---- body
if __arg0[0] != __arg0[1] || __arg0[1] != __arg0[2] {
    assert(__ret0.len() == 3);
    assert(__ret0@ =~= seq!['Y', 'e', 's']);
} else {
    assert(__ret0.len() == 2);
    assert(__ret0@ =~= seq!['N', 'o']);
}
