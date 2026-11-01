use vstd::prelude::*;

verus! {

spec fn presidents_seq() -> Seq<&'static str> {
    seq![
        "Washington", "Adams", "Jefferson", "Madison", "Monroe", "Adams", "Jackson",
        "Van Buren", "Harrison", "Tyler", "Polk", "Taylor", "Fillmore", "Pierce",
        "Buchanan", "Lincoln", "Johnson", "Grant", "Hayes", "Garfield", "Arthur",
        "Cleveland", "Harrison", "Cleveland", "McKinley", "Roosevelt", "Taft",
        "Wilson", "Harding", "Coolidge", "Hoover", "Roosevelt", "Truman",
        "Eisenhower", "Kennedy", "Johnson", "Nixon", "Ford", "Carter", "Reagan"
    ]
}

exec fn get_presidents() -> (result: Vec<&'static str>)
    ensures
        result@ == presidents_seq(),
        result@.len() == 40,
{
    vec![
        "Washington", "Adams", "Jefferson", "Madison", "Monroe", "Adams", "Jackson",
        "Van Buren", "Harrison", "Tyler", "Polk", "Taylor", "Fillmore", "Pierce",
        "Buchanan", "Lincoln", "Johnson", "Grant", "Hayes", "Garfield", "Arthur",
        "Cleveland", "Harrison", "Cleveland", "McKinley", "Roosevelt", "Taft",
        "Wilson", "Harding", "Coolidge", "Hoover", "Roosevelt", "Truman",
        "Eisenhower", "Kennedy", "Johnson", "Nixon", "Ford", "Carter", "Reagan"
    ]
}

fn solve(a: i8) -> (result: &'static str)
    ensures
        if 1 <= a && a <= 40 {
            result == presidents_seq()[a as int - 1]
        } else {
            result == "Washington"
        },
{
    let pres = get_presidents();
    match a {
        1 => "Washington",
        2 => "Adams",
        3 => "Jefferson",
        4 => "Madison",
        5 => "Monroe",
        6 => "Adams",
        7 => "Jackson",
        8 => "Van Buren",
        9 => "Harrison",
        10 => "Tyler",
        11 => "Polk",
        12 => "Taylor",
        13 => "Fillmore",
        14 => "Pierce",
        15 => "Buchanan",
        16 => "Lincoln",
        17 => "Johnson",
        18 => "Grant",
        19 => "Hayes",
        20 => "Garfield",
        21 => "Arthur",
        22 => "Cleveland",
        23 => "Harrison",
        24 => "Cleveland",
        25 => "McKinley",
        26 => "Roosevelt",
        27 => "Taft",
        28 => "Wilson",
        29 => "Harding",
        30 => "Coolidge",
        31 => "Hoover",
        32 => "Roosevelt",
        33 => "Truman",
        34 => "Eisenhower",
        35 => "Kennedy",
        36 => "Johnson",
        37 => "Nixon",
        38 => "Ford",
        39 => "Carter",
        40 => "Reagan",
        _ => {
            "Washington"
        }
    }
}

} // verus!

fn main() {}