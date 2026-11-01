proof fn helper_eq(d: nat)
    requires d < 10,
    ensures factorial(d as int) == spec_factorial(d) as int,
            spec_factorial(d) <= 362880,
{
    reveal_with_fuel(spec_factorial, 11);
    lemma_factorial_0();
    lemma_factorial_1();
    lemma_factorial_2();
    lemma_factorial_3();
    lemma_factorial_4();
    lemma_factorial_5();
    lemma_factorial_6();
    lemma_factorial_7();
    lemma_factorial_8();
    lemma_factorial_9();
    if d == 0 {} else if d == 1 {} else if d == 2 {} else if d == 3 {} else if d == 4 {}
    else if d == 5 {} else if d == 6 {} else if d == 7 {} else if d == 8 {} else {
        assert(d == 9);
    }
}
// ---- body
let d = (__arg0 % 10) as nat;
assert(d < 10);
helper_eq(d);
