// Proves that the Claude contracts the evaluator flagged on VT0256, VA0080 and
// VA0515 imply the reference postconditions (gen post => ref post).
use vstd::prelude::*;
verus! {

// VT0256: every extra reference clause is a fact about bitwise AND itself.
proof fn vt0256_and_facts(a: u8, b: u8)
    ensures
        (a & b) == (b & a),
        (a & 0) == 0,
        (a & a) == a,
        (a & b) <= a,
        (a & b) <= b,
{
    assert((a & b) == (b & a)) by (bit_vector);
    assert((a & 0) == 0) by (bit_vector);
    assert((a & a) == a) by (bit_vector);
    assert((a & b) <= a) by (bit_vector);
    assert((a & b) <= b) by (bit_vector);
}

proof fn vt0256_gen_implies_ref(x1: Seq<u8>, x2: Seq<u8>, result: Seq<u8>)
    requires
        x1.len() == x2.len(),
        result.len() == x1.len(),
        forall|k: int| 0 <= k < result.len() ==> result[k] == (x1[k] & x2[k]),
    ensures
        forall|i: int| 0 <= i < result.len() ==>
            result[i] == (x1[i] & x2[i]) &&
            (x1[i] & x2[i]) == (x2[i] & x1[i]) &&
            (x1[i] & 0) == 0 &&
            (x1[i] & x1[i]) == x1[i] &&
            result[i] <= x1[i] && result[i] <= x2[i],
{
    assert forall|i: int| 0 <= i < result.len() implies
        result[i] == (x1[i] & x2[i]) &&
        (x1[i] & x2[i]) == (x2[i] & x1[i]) &&
        (x1[i] & 0) == 0 &&
        (x1[i] & x1[i]) == x1[i] &&
        result[i] <= x1[i] && result[i] <= x2[i] by {
        vt0256_and_facts(x1[i], x2[i]);
    }
}

// VA0080: Haiku's exact description of the code implies the reference's h-based spec.
spec fn h(x: int, y: int) -> int { x * x + 2 * x * y + x + 1 }

proof fn va0080_gen_implies_ref(r: int, s: Seq<int>)
    requires
        r > 0,
        (r > 4 && r % 2 == 1) ==> (s.len() == 2 && s[0] == 1 && s[1] == (r - 3) / 2),
        !(r > 4 && r % 2 == 1) ==> s.len() == 0,
    ensures
        s.len() == 0 || s.len() == 2,
        s.len() == 2 ==> s[0] > 0 && s[1] > 0,
        s.len() == 2 ==> h(s[0], s[1]) == r,
        r <= 4 ==> s.len() == 0,
        r > 4 && r % 2 == 0 ==> s.len() == 0,
        r > 4 && r % 2 == 1 ==> s.len() == 2 && s[0] == 1 && s[1] == (r - 3) / 2,
{
    if r > 4 && r % 2 == 1 {
        let y = (r - 3) / 2;
        assert(2 * y == r - 3);
        assert(h(1, y) == 1 + 2 * y + 1 + 1) by (nonlinear_arith);
    }
}

// VA0515: Haiku's byte output is exactly the reference's "Yes\n" / "No\n" chars.
spec fn expected_output(temp: int) -> Seq<char> {
    if temp >= 30 { seq!['Y', 'e', 's', '\n'] } else { seq!['N', 'o', '\n'] }
}

proof fn va0515_gen_implies_ref(temp: int, v: Seq<u8>)
    requires
        v == (if temp >= 30 { seq![89u8, 101u8, 115u8, 10u8] } else { seq![78u8, 111u8, 10u8] }),
    ensures
        v.map(|i: int, b: u8| b as char) == expected_output(temp),
{
    assert(v.map(|i: int, b: u8| b as char) =~= expected_output(temp));
}

fn main() {}
}
