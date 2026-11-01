"""Splice proofs into the evaluator's unconditional L2 harnesses, for the four implications in finding 1.

Harnesses come from analysis/unconditional_l2.py --dump and embed the release's references, so they
are not committed. Check each output with Verus; below_zero needs --crate-type=lib.

    python3 -I proofs/splice_unconditional.py <harness dir> <out dir>
"""
import re
import sys
from pathlib import Path

HARNESS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
src = (Path(__file__).parent / "below_zero_equiv.rs").read_text()
a=src.index('proof fn lemma_sum_drop_last'); b=src.index('fn main()')
bz=src[a:b].replace('lemma_sum_drop_last','x_sum_drop_last').replace('lemma_same_sum','x_same_sum').replace('contracts_equivalent','x_contracts_equivalent')
P={
'VeriCoding_VT0256_vericoded__bitwise_and':("""
proof fn x_and_facts(a: u8, b: u8)
    ensures (a & b) == (b & a), (a & 0) == 0, (a & a) == a, (a & b) <= a, (a & b) <= b,
{
    assert((a & b) == (b & a)) by (bit_vector);
    assert((a & 0) == 0) by (bit_vector);
    assert((a & a) == a) by (bit_vector);
    assert((a & b) <= a) by (bit_vector);
    assert((a & b) <= b) by (bit_vector);
}
""","""
    let x1 = __arg0; let x2 = __arg1; let result = __ret0;
    assert forall|i: int| 0 <= i < result@.len() implies
        result@[i] == (x1@[i] & x2@[i]) && (x1@[i] & x2@[i]) == (x2@[i] & x1@[i]) && (x1@[i] & 0) == 0
        && (x1@[i] & x1@[i]) == x1@[i] && result@[i] <= x1@[i] && result@[i] <= x2@[i] by {
        x_and_facts(x1@[i], x2@[i]);
    }
"""),
'VeriCoding_VA0080_vericoded__solve':("","""
    let r = __arg0 as int;
    let m = __ret0@.map(|i: int, x: i8| x as int);
    if r > 4 && r % 2 == 1 {
        let y = (r - 3) / 2;
        assert(2 * y == r - 3);
        assert(h(1, y) == 1 + 2 * y + 1 + 1) by (nonlinear_arith);
        assert(__ret0@[0] as int == 1 && __ret0@[1] as int == y);
        assert(m[0] == 1 && m[1] == y);
    }
"""),
'VeriCoding_VA0515_vericoded__build_output_vec':("","""
    assert(__ret0@.map(|i: int, b: u8| b as char) =~= expected_output(__arg0 as int));
"""),
'VeriCoding_VA0515_vericoded__solve':("","""
    assert(__ret0@.map(|i: int, b: u8| b as char) =~= expected_output(__arg0 as int));
"""),
'HumanEval-Verus_task_6__below_zero':(bz,"""
    let ops = __arg0@;
    if exists|i: int| 0 <= i <= ops.len() && #[trigger] prefix_sum(ops.subrange(0, i)) < 0 {
        let i = choose|i: int| 0 <= i <= ops.len() && #[trigger] prefix_sum(ops.subrange(0, i)) < 0;
        x_contracts_equivalent(ops, i);
        assert(sum(first_n(ops, i)) < 0);
    }
    if exists|i: int| 0 <= i <= ops.len() && #[trigger] sum(first_n(ops, i)) < 0 {
        let i = choose|i: int| 0 <= i <= ops.len() && #[trigger] sum(first_n(ops, i)) < 0;
        x_contracts_equivalent(ops, i);
        assert(prefix_sum(ops.subrange(0, i)) < 0);
    }
"""),
}
for name,(helpers,body) in P.items():
    h=(HARNESS / f'{name}.rs').read_text()
    s=h.index('proof fn lemma_sqm_')
    m=re.compile(r'\{\s*\}').search(h,s)
    (OUT / f'{name}.rs').write_text(h[:s]+helpers+'\n'+h[s:m.start()]+'{'+body+'}'+h[m.end():])
