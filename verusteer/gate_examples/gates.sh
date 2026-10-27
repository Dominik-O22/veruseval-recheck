#!/bin/sh
# Which edits each pipeline's code-change check accepts.
# AutoVerus uses `lynette compare -t`; VeruSAGE uses `lynette additions`.
#   sh gates.sh /path/to/lynette
L=${1:?usage: gates.sh /path/to/lynette}
cd "$(dirname "$0")"
row() {
    "$L" compare -t "$2" "$3" >/dev/null 2>&1 && a=allow || a=reject
    "$L" additions "$2" "$3" >/dev/null 2>&1 && v=allow || v=reject
    printf "%-52s %-10s %-10s\n" "$1" "$a" "$v"
}
printf "%-52s %-10s %-10s\n" edit AutoVerus VeruSAGE
row "add a loop invariant" loop_original.rs loop_add_invariant.rs
row "add a proof fn" loop_original.rs loop_add_proof_fn.rs
row "add an import" loop_original.rs loop_add_import.rs
row "remove an import that does not resolve" import_broken.rs import_removed.rs
row "rewrite a spec fn body to true" spec_fn_original.rs spec_fn_weakened.rs
row "change exec code in an if whose else is proof-only" if_with_proof_only_else.rs if_with_proof_only_else_exec_changed.rs
