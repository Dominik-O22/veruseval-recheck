// ---- body
assert forall|k: int| 0 <= k < __ret0 as int implies
    #[trigger] __arg0@.subrange(0, __ret0 as int)[k] == __arg1@.subrange(0, __ret0 as int)[k] by {
    assert(__arg0[k] == __arg1[k]);
}
assert(__arg0@.subrange(0, __ret0 as int) =~= __arg1@.subrange(0, __ret0 as int));
