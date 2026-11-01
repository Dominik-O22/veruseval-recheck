// ---- body
if __arg0 < 1200 {
    assert(__ret0@ =~= seq!['A', 'B', 'C', '\n']);
} else {
    assert(__ret0@ =~= seq!['A', 'R', 'C', '\n']);
}
