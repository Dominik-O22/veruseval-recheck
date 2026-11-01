proof fn bv_and_facts(a: u8, b: u8)
    ensures
        (a & b) == (b & a),
        (a & 0u8) == 0u8,
        (a & a) == a,
        (a & b) <= a,
        (a & b) <= b,
{
    assert((a & b) == (b & a)) by (bit_vector);
    assert((a & 0u8) == 0u8) by (bit_vector);
    assert((a & a) == a) by (bit_vector);
    assert((a & b) <= a) by (bit_vector);
    assert((a & b) <= b) by (bit_vector);
}
// ---- body
assert forall|i: int| 0 <= i < __ret0@.len() implies
    __ret0@[i] == (__arg0@[i] & __arg1@[i]) &&
    (__arg0@[i] & __arg1@[i]) == (__arg1@[i] & __arg0@[i]) &&
    (__arg0@[i] & 0) == 0 &&
    (__arg0@[i] & __arg0@[i]) == __arg0@[i] &&
    __ret0@[i] <= __arg0@[i] && __ret0@[i] <= __arg1@[i] by {
    bv_and_facts(__arg0@[i], __arg1@[i]);
    assert(__ret0[i] == (__arg0[i] & __arg1[i]));
}
