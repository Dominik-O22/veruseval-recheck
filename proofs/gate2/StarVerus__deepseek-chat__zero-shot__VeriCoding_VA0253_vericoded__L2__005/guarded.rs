// ---- body
let am = __arg2@.map(|i: int, x: i8| x as int);
if all_elements_greater_than_s(am, __arg1 as int) {
    assert(am.len() == __arg2.len());
    assert(forall|i: int| 0 <= i < __arg2.len() ==> am[i] == __arg2@[i] as int);
    assert(forall|i: int| 0 <= i && i < __arg2.len() ==> __arg2[i] > __arg1) by {
        assert forall|i: int| 0 <= i && i < __arg2.len() implies __arg2[i] > __arg1 by {
            assert(am[i] == __arg2@[i] as int);
            assert(am[i] > __arg1 as int);
        }
    }
    assert(am[0] > __arg1 as int);
}
