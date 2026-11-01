// ---- body
assert forall|i: int| 0 <= i < __arg0.len() implies (__ret0@.index(i) == false <==> exists|val: i64| __arg0@.index(i) == DateTime64::Valid(val)) by {
    lemma_not_nat_iff_exists_valid(__arg0@.index(i));
    assert(__ret0[i] == __ret0@.index(i));
    assert(__arg0[i] == __arg0@.index(i));
}
