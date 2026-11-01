// <vc-preamble>
use vstd::prelude::*;

verus! {
// </vc-preamble>

// <vc-helpers>
// </vc-helpers>

// <vc-spec>
fn meshgrid(x: Vec<f32>, y: Vec<f32>) -> (result: (Vec<Vec<f32>>, Vec<Vec<f32>>))
    ensures
        result.0.len() == y.len(),
        result.1.len() == y.len(),
        forall|i: int| 0 <= i < y.len() ==> result.0[i].len() == x.len() && result.1[i].len() == x.len(),
        forall|i: int, j: int| 0 <= i < y.len() && 0 <= j < x.len() ==>
            #[trigger] result.0[i][j] == x[j] && #[trigger] result.1[i][j] == y[i],
// </vc-spec>
// <vc-code>
{
    let mut xx: Vec<Vec<f32>> = Vec::new();
    let mut yy: Vec<Vec<f32>> = Vec::new();
    let mut i = 0;
    while i < y.len()
        invariant
            i <= y.len(),
            xx.len() == i,
            yy.len() == i,
            forall|k: int| 0 <= k < i ==> xx[k].len() == x.len() && yy[k].len() == x.len(),
            forall|k: int, j: int| 0 <= k < i && 0 <= j < x.len() ==>
                xx[k][j] == x[j] && yy[k][j] == y[k],
        decreases (y.len() - i) as int
    {
        let mut x_row: Vec<f32> = Vec::new();
        let mut y_row: Vec<f32> = Vec::new();
        let mut j = 0;
        while j < x.len()
            invariant
                i < y.len(),
                j <= x.len(),
                x_row.len() == j,
                y_row.len() == j,
                forall|m: int| 0 <= m < j ==> x_row[m] == x[m] && y_row[m] == y[i as int],
            decreases (x.len() - j) as int
        {
            x_row.push(x[j]);
            y_row.push(y[i]);
            j += 1;
        }
        assert(x_row.len() == x.len());
        assert(y_row.len() == x.len());
        xx.push(x_row);
        yy.push(y_row);
        i += 1;
    }
    (xx, yy)
}
// </vc-code>

}
fn main() {}