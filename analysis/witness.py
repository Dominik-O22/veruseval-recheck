"""Literal-witness counterexample engine for VerusEval clause lemmas (gate 2).

A proposer returns literal values only. A fixed template binds them and asserts the antecedent
and the negated consequent of one clause lemma, following the release's concrete-value engine in
metrics_rebuild/share/contract_eval.py:

    proof fn __witness(<the lemma's own parameters>)
        requires <each parameter pinned to its literal: x == 5i32, a@ == seq![1i32, 2i32], ...>
    {
        reveal_with_fuel(<recursive spec fn>, k);    // only where a clause reaches one
        assert(<antecedent wrapper call>);           // one per antecedent clause
        assert(!(<consequent wrapper call>));
    }

There are no loops, branches or calls in it. Everything except the lemma comes unchanged from the
harness that the release's own per-clause path builds (the reference file, copied support items and
the per-clause wrapper spec fns), so the witness talks about exactly the formula the release checks.
Because every parameter of the lemma is a parameter of the witness, a verified witness shows that
the lemma's requires hold and its ensures fail at the pinned values, which refutes the lemma.

Only a positive Verus result produces a verdict. The same file with the body replaced by
assert(false) is run as a control. If it verifies, the pins or the context are inconsistent and the
verdict is void. A timeout, a failed run or a compile error is never a verdict.

Where the types allow it, a confirmed witness is also built by exec code (vec![..], literals) in a
Verus-verified exec fn that asserts the same formulas, compiled with --compile and run. A witness
that only exists as a proof-side value, for example a Vec whose length exceeds what memory allows,
is reported as its own class.

Run from the VerusEval release root with Verus on PATH. See --help.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Optional

ROOT = Path.cwd()
VERUS = os.environ.get("VERUS_PATH", "verus")
SCREEN_BATCH = 24          # candidates per screening batch
SCREEN_RLIMIT = 2          # SMT budget per candidate during screening
CONFIRM_RLIMIT = 10        # the release's default
POOL_CAP = 400             # candidates generated before ranking
COMPUTED_CAP = 72          # computed-value candidates per lemma
FUEL_MIN, FUEL_MAX = 12, 64
TIMING: dict[str, float] = {"verus_seconds": 0.0, "verus_runs": 0}

INT_BOUNDS = {
    "u8": (0, 2**8 - 1), "u16": (0, 2**16 - 1), "u32": (0, 2**32 - 1), "u64": (0, 2**64 - 1),
    "u128": (0, 2**128 - 1), "usize": (0, 2**64 - 1),
    "i8": (-(2**7), 2**7 - 1), "i16": (-(2**15), 2**15 - 1), "i32": (-(2**31), 2**31 - 1),
    "i64": (-(2**63), 2**63 - 1), "i128": (-(2**127), 2**127 - 1), "isize": (-(2**63), 2**63 - 1),
}
INT_SIZES = {"u8": 1, "u16": 2, "u32": 4, "u64": 8, "u128": 16, "usize": 8, "i8": 1, "i16": 2,
             "i32": 4, "i64": 8, "i128": 16, "isize": 8, "bool": 1, "char": 4, "f32": 4, "f64": 8}
ISIZE_MAX = 2**63 - 1


def release_imports():
    sys.path.insert(0, str(ROOT))
    global li, ce, smt_mod, functions_mod, type_defs, shared_mod, io_cases
    import metrics_rebuild.share.lemma_implication as li
    import metrics_rebuild.share.contract_eval as ce
    import metrics_rebuild.share.smt as smt_mod
    import metrics_rebuild.share.functions as functions_mod
    import metrics_rebuild.share.type_defs as type_defs
    import metrics_rebuild.share._shared as shared_mod
    import metrics_rebuild.share.io_cases as io_cases
    li.set_lemma_verus_binary(VERUS)


# --------------------------------------------------------------------------- types

def split_top(text: str, sep: str = ",") -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "<([{":
            depth += 1
        elif ch in ">)]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def parse_type(text: str, registry: Optional[dict] = None) -> tuple:
    t = re.sub(r"\s+", " ", str(text).strip())
    t = re.sub(r"^&\s*'[A-Za-z_]\w*\s*", "&", t)
    if t.startswith("&"):
        inner = t[1:].strip()
        if inner.startswith("mut "):
            inner = inner[4:]
        if inner == "str":
            return ("str",)
        return ("ref", parse_type(inner, registry))
    if registry:
        alias = type_defs.resolve_alias_text(registry, t)
        if alias != t:
            return parse_type(alias, registry)
    if t in INT_BOUNDS:
        return ("int", t)
    if t in ("int", "nat"):
        return ("math", t)
    if t == "bool":
        return ("bool",)
    if t == "char":
        return ("char",)
    if t in ("f32", "f64"):
        return ("float", t)
    if t in ("String", "str"):
        return ("string",) if t == "String" else ("str",)
    if t == "()":
        return ("unit",)
    m = re.fullmatch(r"(Vec|Seq|Box|Option|Ghost|Tracked)\s*<(.*)>", t)
    if m:
        kind, inner = m.group(1), parse_type(m.group(2), registry)
        return {"Vec": ("vec", inner), "Seq": ("seq", inner), "Box": ("box", inner),
                "Option": ("option", inner)}.get(kind, ("unsupported", t))
    m = re.fullmatch(r"\[(.*);\s*(\d+)\s*\]", t)
    if m:
        return ("array", parse_type(m.group(1), registry), int(m.group(2)))
    m = re.fullmatch(r"\[(.*)\]", t)
    if m:
        return ("slice", parse_type(m.group(1), registry))
    if t.startswith("(") and t.endswith(")"):
        return ("tuple", tuple(parse_type(p, registry) for p in split_top(t[1:-1])))
    entry = type_defs.registry_entry(registry, t) if registry else None
    if entry is not None:
        name = type_defs.registry_type_name(t)
        if entry["kind"] == "enum":
            return ("enum", name, tuple(entry["variants"]))
        return ("struct", name, tuple((f, parse_type(ft, registry)) for f, ft in entry["fields"]),
                bool(entry.get("tuple")))
    return ("unsupported", t)


def type_class(ty: tuple) -> set[str]:
    """Type classes a lemma parameter belongs to, for the per-class report."""
    kind = ty[0]
    if kind == "ref":
        return type_class(ty[1])
    if kind in ("vec", "seq", "box", "option"):
        own = {"vec": "Vec", "seq": "Seq", "box": "Box", "option": "Option"}[kind]
        return {own} | type_class(ty[1])
    if kind == "slice":
        return {"slice"} | type_class(ty[1])
    if kind == "array":
        return {"array"} | type_class(ty[1])
    if kind == "tuple":
        return {"tuple"}.union(*(type_class(t) for t in ty[1]))
    if kind == "struct":
        return {"struct"}.union(*(type_class(t) for _, t in ty[2]))
    return {{"int": "integer", "math": "int/nat", "bool": "bool", "char": "char", "float": "float",
             "string": "string", "str": "string", "enum": "enum", "unit": "unit"}.get(kind, "unsupported")}


def contains_unsupported(ty: tuple) -> bool:
    if ty[0] == "unsupported":
        return True
    if ty[0] in ("ref", "vec", "seq", "box", "option", "slice", "array"):
        return contains_unsupported(ty[1])
    if ty[0] == "tuple":
        return any(contains_unsupported(t) for t in ty[1])
    if ty[0] == "struct":
        return any(contains_unsupported(t) for _, t in ty[2])
    return False


# --------------------------------------------------------------------------- literals and pins

class LiteralError(ValueError):
    pass


def int_literal(value: Any, name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LiteralError(f"not an integer for {name}: {value!r}")
    low, high = INT_BOUNDS[name]
    if not low <= value <= high:
        raise LiteralError(f"{value} out of range for {name}")
    return f"{value}{name}"


def char_literal(value: Any) -> str:
    if isinstance(value, str) and len(value) == 1:
        code = ord(value)
    elif isinstance(value, int) and not isinstance(value, bool):
        code = value
    else:
        raise LiteralError(f"not a char: {value!r}")
    if code < 0 or code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
        raise LiteralError(f"not a Unicode scalar value: {code}")
    return ce._verus_char_literal(code)


def float_literal(value: Any, name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LiteralError(f"not a float: {value!r}")
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise LiteralError("non-finite float literals are not bound")
    text = repr(abs(value))
    if "e" not in text and "." not in text:
        text += ".0"
    return f"{'-' if value < 0 or (value == 0 and str(value).startswith('-')) else ''}{text}{name}"


def scalar_literal(ty: tuple, value: Any) -> Optional[str]:
    kind = ty[0]
    if kind == "int":
        return int_literal(value, ty[1])
    if kind == "math":
        if isinstance(value, bool) or not isinstance(value, int) or (ty[1] == "nat" and value < 0):
            raise LiteralError(f"bad {ty[1]} {value!r}")
        return f"{value}int" if ty[1] == "int" else f"{value}nat"
    if kind == "bool":
        if not isinstance(value, bool):
            raise LiteralError(f"not a bool: {value!r}")
        return "true" if value else "false"
    if kind == "char":
        return char_literal(value)
    if kind == "float":
        return float_literal(value, ty[1])
    return None


def is_scalar(ty: tuple) -> bool:
    return ty[0] in ("int", "math", "bool", "char", "float")


def is_length_only(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"len"}


# A computed value is {"computed": "<spec expression>"} in place of a scalar literal. It lets a witness
# depend on a value Verus leaves unspecified, such as a read past the end of a sequence. The grammar has
# reads, ==, if and suffixed literals only: no arithmetic, so the expression stays in its slot's type,
# and no calls or quantifiers. Such a witness has no single concrete input, so it is tagged and never run.
SLOT = re.compile(r"__old_arg\d+|__arg\d+|__ret\d+")
COMPUTED_EXPR = re.compile(r"(?:\s|__old_arg\d+|__arg\d+|__ret\d+|@|\[-?\d+\]|[(){}]|==|\bif\b|\belse\b|\btrue\b|\bfalse\b"
                           r"|-?\d+(?:\.\d+)?(?:[iu](?:8|16|32|64|128|size)|f32|f64))+")


def is_computed(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"computed"}


def computed_leaves(value: Any) -> Iterable[dict]:
    if is_computed(value):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from computed_leaves(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from computed_leaves(v)


def check_computed(assignment: dict) -> None:
    """A computed value may read only parameters bound to plain literals, never itself or another
    computed value, so the pins always have a solution. Raises LiteralError."""
    plain = {slot for slot, value in assignment.items() if not any(computed_leaves(value))}
    for value in assignment.values():
        for leaf in computed_leaves(value):
            text = leaf["computed"]
            if not COMPUTED_EXPR.fullmatch(text) or not set(SLOT.findall(text)) <= plain:
                raise LiteralError(f"bad computed value {text!r}")


def pins(expr: str, ty: tuple, value: Any) -> list[str]:
    """Spec clauses that pin ``expr`` (of type ``ty``) to ``value``. Raises LiteralError."""
    kind = ty[0]
    if kind == "ref":
        inner = ty[1]
        if inner[0] in ("vec", "slice", "array", "string", "box"):
            return pins(expr, inner, value)
        return pins(f"(*{expr})", inner, value)
    if kind == "box":
        return pins(f"(*{expr})", ty[1], value)
    if kind == "unit":
        return []
    if is_computed(value):
        if not is_scalar(ty):
            raise LiteralError(f"computed value at non-scalar type {ty!r}")
        return [f"{expr} == ({value['computed']})"]
    lit = scalar_literal(ty, value) if is_scalar(ty) else None
    if lit is not None:
        if ty[0] == "int" and ty[1] in ("usize", "isize") and not -(2**31) <= value <= 2**32 - 1:
            # Verus rejects such suffixed literals while the word size is open; compare as int.
            return [f"({expr} as int) == {value}"]
        return [f"{expr} == {lit}"]
    if kind in ("vec", "slice", "array", "seq"):
        view = expr if kind == "seq" else f"{expr}@"
        elem = ty[1]
        if is_length_only(value):
            n = value["len"]
            if not isinstance(n, int) or n < 0 or n > INT_BOUNDS["usize"][1]:
                raise LiteralError(f"bad length {n!r}")
            if kind == "array" and n != ty[2]:
                raise LiteralError("array length mismatch")
            return [f"{view}.len() == {n}"]
        if isinstance(value, str) and elem[0] == "char":
            value = list(value)
        if not isinstance(value, list):
            raise LiteralError(f"not a sequence: {value!r}")
        if kind == "array" and len(value) != ty[2]:
            raise LiteralError("array length mismatch")
        if is_scalar(elem) and value and not any(map(is_computed, value)):
            out = [f"{view} == seq![{', '.join(scalar_literal(elem, v) for v in value)}]"]
            out += [f"{view}[{i}] == {scalar_literal(elem, v)}" for i, v in enumerate(value)]
            return out
        out = [f"{view}.len() == {len(value)}"]
        for i, v in enumerate(value):
            out += pins(f"{view}[{i}]", elem, v)
        return out
    if kind in ("string", "str"):
        if is_length_only(value):
            return [f"{expr}@.len() == {value['len']}"]
        if isinstance(value, list):
            value = "".join(value)
        if not isinstance(value, str):
            raise LiteralError(f"not a string: {value!r}")
        if not value:
            return [f"{expr}@.len() == 0"]
        chars = [char_literal(c) for c in value]
        return ([f"{expr}@ == seq![{', '.join(chars)}]"] +
                [f"{expr}@[{i}] == {c}" for i, c in enumerate(chars)])
    if kind == "option":
        if value is None:
            return [f"{expr} is None"]
        if isinstance(value, dict) and set(value) == {"Some"}:
            value = value["Some"]
        return [f"{expr} is Some"] + pins(f"{expr}->Some_0", ty[1], value)
    if kind == "tuple":
        if not isinstance(value, (list, tuple)) or len(value) != len(ty[1]):
            raise LiteralError(f"bad tuple {value!r}")
        out = []
        for i, (t, v) in enumerate(zip(ty[1], value)):
            out += pins(f"({expr}).{i}", t, v)
        return out
    if kind == "struct":
        _, _name, fields, _tuple = ty
        if isinstance(value, dict):
            values = [value[f] for f, _ in fields]
        elif isinstance(value, (list, tuple)) and len(value) == len(fields):
            values = list(value)
        else:
            raise LiteralError(f"bad struct value {value!r}")
        out = []
        for (fname, ftype), v in zip(fields, values):
            out += pins(f"({expr}).{fname}", ftype, v)
        return out
    if kind == "enum":
        if not isinstance(value, str) or value not in ty[2]:
            raise LiteralError(f"bad enum value {value!r}")
        return [f"{expr} is {value}"]
    raise LiteralError(f"unsupported type {ty!r}")


def exec_literal(ty: tuple, value: Any) -> str:
    """An exec expression that builds ``value``. Raises LiteralError where none exists here."""
    kind = ty[0]
    if kind in ("int", "bool", "char", "float"):
        return scalar_literal(ty, value)
    if kind == "math":
        raise LiteralError("ghost type")
    if kind == "vec":
        if is_length_only(value):
            n = value["len"]
            size = INT_SIZES.get(ty[1][1] if ty[1][0] in ("int", "float") else ty[1][0], 8)
            if n * size > ISIZE_MAX:
                raise LiteralError("unrepresentable: allocation exceeds isize::MAX bytes")
            if n > 1_000_000:
                raise LiteralError("too large to build here")
            raise LiteralError("length-only value with unconstrained elements")
        if not isinstance(value, list):
            raise LiteralError("not a list")
        return f"vec![{', '.join(exec_literal(ty[1], v) for v in value)}]"
    if kind == "array":
        return f"[{', '.join(exec_literal(ty[1], v) for v in value)}]"
    if kind == "tuple":
        parts = [exec_literal(t, v) for t, v in zip(ty[1], value)]
        return f"({', '.join(parts)}{',' if len(parts) == 1 else ''})"
    if kind == "option":
        if value is None:
            return "None"
        if isinstance(value, dict) and set(value) == {"Some"}:
            value = value["Some"]
        return f"Some({exec_literal(ty[1], value)})"
    if kind == "struct":
        _, name, fields, tuple_struct = ty
        values = [value[f] for f, _ in fields] if isinstance(value, dict) else list(value)
        parts = [exec_literal(t, v) for (_, t), v in zip(fields, values)]
        if tuple_struct:
            return f"{name}({', '.join(parts)})"
        return f"{name} {{ {', '.join(f'{f}: {p}' for (f, _), p in zip(fields, parts))} }}"
    if kind == "enum":
        return f"{ty[1]}::{value}"
    if kind in ("str", "string"):
        if isinstance(value, list):
            value = "".join(value)
        if not isinstance(value, str):
            raise LiteralError("not a string")
        literal = json.dumps(value, ensure_ascii=False)
        return literal if kind == "str" else f"String::from_str({literal})"
    raise LiteralError(f"no exec constructor for {ty!r}")


# --------------------------------------------------------------------------- obligations

@dataclass
class Wrapper:
    name: str
    body: str
    params: list[tuple[str, str, str]]       # (wrapper parameter name, type, lemma argument)


@dataclass
class Lemma:
    key: str
    sample: str
    direction: str
    form: str
    check: str
    function: str
    release_status: Optional[str]
    release_reason: Optional[str]
    harness: Optional[str] = None
    lemma_text: Optional[str] = None
    lemma_name: Optional[str] = None
    params: list[tuple[str, str]] = field(default_factory=list)
    antecedent: list[str] = field(default_factory=list)
    consequent: list[str] = field(default_factory=list)
    wrappers: dict[str, Wrapper] = field(default_factory=dict)
    slots: dict[str, dict] = field(default_factory=dict)   # lemma param -> role, source name, type
    generic_parameters: str = ""


class Recorder:
    """Records what the release's per-clause path builds, without changing it."""

    def __init__(self):
        self.lemmas: dict[str, dict] = {}
        self.pending_wrappers: dict[str, Any] = {}
        self.last: Optional[str] = None

    @contextmanager
    def active(self):
        original_make, original_wrap, original_run = li._make_lemma, li.build_clause_wrapper, li.subprocess.run

        def make(name, params, antecedent, consequent, **kw):
            text = original_make(name, params, antecedent, consequent, **kw)
            self.lemmas[name] = {"text": text, "params": [(p["name"], p["type"]) for p in params],
                                 "antecedent": list(antecedent), "consequent": list(consequent),
                                 "wrappers": dict(self.pending_wrappers), "harness": None,
                                 "generic_parameters": kw.get("generic_parameters", "")}
            self.last = name
            return text

        def wrap(plan, clause, *, wrapper_name):
            result = original_wrap(plan, clause, wrapper_name=wrapper_name)
            if result.wrapper is not None:
                self.pending_wrappers[wrapper_name] = result.wrapper
            return result

        def run(cmd, *a, **k):
            if isinstance(cmd, list) and self.last and self.lemmas.get(self.last):
                path = Path(cmd[-1])
                if path.suffix == ".rs" and path.exists():
                    self.lemmas[self.last]["harness"] = path.read_text()
            started = time.monotonic()
            try:
                return original_run(cmd, *a, **k)
            finally:
                TIMING["verus_seconds"] += time.monotonic() - started
                TIMING["verus_runs"] += 1

        li._make_lemma, li.build_clause_wrapper, li.subprocess.run = make, wrap, run
        try:
            yield self
        finally:
            li._make_lemma, li.build_clause_wrapper, li.subprocess.run = original_make, original_wrap, original_run


def _function_context(path: str, function: str) -> Optional[dict]:
    for context in functions_mod.strength_contexts_for_path(path):
        if context.get("function") == function:
            return context
    return None


DIRECTION_ARGS = {
    "L1": dict(source_side="generated", clause_kind="requires",
               implication_direction="reference_implies_generated_clause"),
    "L2": dict(source_side="reference", clause_kind="ensures",
               implication_direction="generated_implies_reference_clause"),
}


def capture(sample: str, generated: str, reference: str, function: str, direction: str,
            form: str) -> list[Lemma]:
    """Run the release's per-clause check for one function and record each clause lemma."""
    gen_ctx = _function_context(generated, function)
    ref_ctx = _function_context(reference, function)
    if gen_ctx is None or ref_ctx is None:
        return []
    li._LEMMA_CACHE.clear()
    recorder = Recorder()
    with recorder.active():
        if form == "unconditional" or direction == "L1":
            result = smt_mod.clause_implication_details_for_context(
                candidate=gen_ctx, reference=ref_ctx, reference_rs_path=reference,
                generated_rs_path=generated, **DIRECTION_ARGS[direction])
            details = result.get("details") or []
        else:   # guarded L2: both preconditions added to the antecedent
            materialize = shared_mod.materialize_contract_clauses
            implicit = shared_mod.IMPLICIT_TRUE_CONTRACT_CLAUSES_DEFAULT
            ref_req = materialize(ref_ctx.get("requires") or [], kind="requires", inject_implicit_true=False)
            gen_req = materialize(gen_ctx.get("requires") or [], kind="requires", inject_implicit_true=False)
            gen_ens = materialize(gen_ctx.get("ensures") or [], kind="ensures", inject_implicit_true=implicit)
            ref_ens = materialize(ref_ctx.get("ensures") or [], kind="ensures", inject_implicit_true=implicit)
            tag = smt_mod._tag_lemma_source
            antecedent = tag(ref_req, "reference") + tag(gen_req, "generated") + tag(gen_ens, "generated")
            details = []
            for index, clause in enumerate(ref_ens, 1):
                check = li.lemma_implication_check(
                    reference_rs_path=reference, reference_context=ref_ctx, generated_context=gen_ctx,
                    function_name=function, check_name=f"guarded_generated_implies_reference_clause_ensures_{index:03d}",
                    antecedent=antecedent, consequent=tag([clause], "reference"), generated_rs_path=generated)
                details.append({"id": f"{function}_ensures_{index:03d}", "implication_check": check})
    binding = li.bind_function_contexts(ref_ctx, gen_ctx)
    plan = binding.plan
    out = []
    for detail in details:
        check = detail.get("implication_check") or {}
        name = (check.get("obligation_context") or {}).get("check_name") or detail.get("id")
        lemma = Lemma(key=f"{sample}|{function}|{direction}|{form}|{name}", sample=sample, direction=direction,
                      form=form, check=name, function=function, release_status=check.get("status"),
                      release_reason=check.get("reason"))
        record = recorder.lemmas.get(check.get("lemma") or "")
        if record and record["harness"] and plan is not None:
            lemma.harness, lemma.lemma_text, lemma.lemma_name = record["harness"], record["text"], check["lemma"]
            lemma.params, lemma.antecedent, lemma.consequent = record["params"], record["antecedent"], record["consequent"]
            lemma.generic_parameters = record["generic_parameters"]
            lemma.wrappers = {n: Wrapper(n, w.body_text, [(p.name, p.rust_type, p.argument) for p in w.parameters])
                              for n, w in record["wrappers"].items()}
            for item in plan.inputs:
                lemma.slots[item.canonical_name] = {"role": "input", "name": item.reference_name,
                                                    "type": item.lemma_type, "mutable": item.mutable}
                if item.mutable:
                    lemma.slots[item.old_canonical_name] = {"role": "old", "name": item.reference_name,
                                                            "type": item.lemma_type, "mutable": True}
            for position, item in enumerate(plan.returns):
                lemma.slots[item.canonical_name] = {"role": "return", "name": item.reference_name,
                                                    "position": position, "type": item.lemma_type}
        out.append(lemma)
    return out


# --------------------------------------------------------------------------- template

def registry_for(lemma: Lemma) -> dict:
    return type_defs.parse_type_definitions(lemma.harness or "")


def recursive_reveals(lemma: Lemma, fuel: int) -> list[str]:
    texts = [lemma.wrappers[c.split("(")[0]].body for c in (*lemma.antecedent, *lemma.consequent)
             if c.split("(")[0] in lemma.wrappers]
    lines = ce._fuel_reveal_lines({"spec_preamble": lemma.harness}, texts)
    return [re.sub(r", 12\);", f", {fuel});", line) for line in lines]


def assumes_64bit(lemma: Lemma, assignment: dict) -> bool:
    """Whether a pin needs usize or isize wider than 32 bits (the witness then speaks about 64-bit targets)."""
    registry = registry_for(lemma)
    for pname, ptype in lemma.params:
        if pname in assignment:
            try:
                clauses = pins(pname, parse_type(ptype, registry), assignment[pname])
            except LiteralError:
                continue
            if any(" as int) == " in c for c in clauses):
                return True
    return False


def fuel_for(assignment: dict) -> int:
    biggest = 0
    for value in assignment.values():
        for leaf in leaves(value):
            if isinstance(leaf, int) and not isinstance(leaf, bool):
                biggest = max(biggest, abs(leaf))
        if isinstance(value, list):
            biggest = max(biggest, len(value))
    return max(FUEL_MIN, min(FUEL_MAX, biggest + 2))


def leaves(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        if is_length_only(value):
            return
        for v in value.values():
            yield from leaves(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from leaves(v)
    else:
        yield value


def witness_fn(lemma: Lemma, assignment: dict, name: str, *, control: bool = False) -> str:
    """The fixed template. Raises LiteralError if a value cannot be bound at its type."""
    registry = registry_for(lemma)
    check_computed(assignment)
    signature = ", ".join(f"{n}: {t}" for n, t in lemma.params)
    requires = []
    for pname, ptype in lemma.params:
        if pname in assignment:
            requires += pins(pname, parse_type(ptype, registry), assignment[pname])
    lines = [f"proof fn {name}{lemma.generic_parameters}({signature})"]
    if requires:
        lines.append("    requires")
        lines += [f"        {clause}," for clause in requires]
    lines.append("{")
    lines += recursive_reveals(lemma, fuel_for(assignment))
    if control:
        lines.append("    assert(false);")
    else:
        lines += [f"    assert({call});" for call in lemma.antecedent]
        lines.append(f"    assert(!({' && '.join(lemma.consequent)}));")
    lines.append("}")
    return "\n".join(lines)


def file_with(lemma: Lemma, items: list[str], main_body: str = "", prefix: str = "") -> str:
    harness = lemma.harness
    assert lemma.lemma_text in harness, "lemma text not found in harness"
    text = harness.replace(lemma.lemma_text, "\n\n".join([prefix, *items] if prefix else items))
    if main_body:
        if re.search(r"\bfn\s+main\s*\(\s*\)\s*\{", text):
            text = re.sub(r"\bfn\s+main\s*\(\s*\)\s*\{", f"fn main() {{ {main_body} ", text, count=1)
        else:
            text += f"\nfn main() {{ {main_body} }}\n"
    return text


@dataclass
class Run:
    verified: int
    errors: int
    encountered_error: bool
    timeout: bool
    returncode: Optional[int]
    stderr: str
    seconds: float


def run_verus(text: str, function: str, *, rlimit: float, timeout: int, extra: list[str] = (),
              keep: Optional[Path] = None) -> Run:
    with tempfile.TemporaryDirectory(prefix="witness_") as tmp:
        path = Path(tmp) / "witness.rs"
        path.write_text(text)
        if keep:
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_text(text)
        cmd = [VERUS, "--output-json", "--crate-type=lib", "--verify-root", "--verify-function", function,
               "--rlimit", str(rlimit), "--num-threads", "1", *extra, str(path)]
        started = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            seconds = time.monotonic() - started
            TIMING["verus_seconds"] += seconds
            TIMING["verus_runs"] += 1
            return Run(0, 0, True, True, None, "timeout", seconds)
        seconds = time.monotonic() - started
        TIMING["verus_seconds"] += seconds
        TIMING["verus_runs"] += 1
    try:
        results = json.loads(proc.stdout)["verification-results"]
    except (json.JSONDecodeError, KeyError):
        return Run(0, 0, True, False, proc.returncode, proc.stderr, seconds)
    return Run(int(results.get("verified") or 0), int(results.get("errors") or 0),
               bool(results.get("encountered-error")), False, proc.returncode, proc.stderr, seconds)


def positive(run: Run) -> bool:
    """The only result that yields a verdict: Verus verified the function, no errors, no timeout."""
    return (not run.timeout and run.returncode == 0 and not run.encountered_error
            and run.verified >= 1 and run.errors == 0)


def failed_lines(stderr: str) -> Optional[set[int]]:
    """Lines of witness.rs with a reported error, or None if the run failed for another reason."""
    lines = set()
    for match in re.finditer(r"--> \S*witness\.rs:(\d+):\d+", stderr):
        lines.add(int(match.group(1)))
    return lines


# --------------------------------------------------------------------------- proposers

def to_assignment(lemma: Lemma, inputs: dict, post: dict, output: dict) -> dict:
    """Map literal values named as in the source signature onto the lemma's parameters."""
    out = {}
    for slot, info in lemma.slots.items():
        name = info["name"]
        if info["role"] == "old":
            if name in inputs:
                out[slot] = inputs[name]
        elif info["role"] == "input":
            if info.get("mutable"):
                if name in post:
                    out[slot] = post[name]
                elif name in inputs:
                    out[slot] = inputs[name]
            elif name in inputs:
                out[slot] = inputs[name]
        else:
            if name in output:
                out[slot] = output[name]
            elif f"__ret{info['position']}" in output:
                out[slot] = output[f"__ret{info['position']}"]
    return out


def default_value(ty: tuple) -> Any:
    kind = ty[0]
    if kind in ("ref", "box"):
        return default_value(ty[1])
    if kind in ("int", "math"):
        return 0
    if kind == "float":
        return 0.0
    if kind == "bool":
        return False
    if kind == "char":
        return "a"
    if kind in ("vec", "slice", "seq"):
        return []
    if kind == "array":
        return [default_value(ty[1])] * ty[2]
    if kind in ("string", "str"):
        return ""
    if kind == "option":
        return None
    if kind == "tuple":
        return [default_value(t) for t in ty[1]]
    if kind == "struct":
        return [default_value(t) for _, t in ty[2]]
    if kind == "enum":
        return ty[2][0]
    return None


def scalar_variants(ty: tuple, value: Any) -> list[Any]:
    kind = ty[0]
    if kind == "int":
        low, high = INT_BOUNDS[ty[1]]
        vals = [value + 1, value - 1, 0, 1, -1, low, high, low + 1, high - 1, 2 * value, -value]
        return [v for v in vals if isinstance(v, int) and low <= v <= high and v != value]
    if kind == "math":
        vals = [value + 1, value - 1, 0, 1, -1, 2 * value, -value]
        return [v for v in vals if v != value and (ty[1] == "int" or v >= 0)]
    if kind == "bool":
        return [not value]
    if kind == "char":
        c = ord(value) if isinstance(value, str) else value
        return [chr(x) for x in (c + 1, c - 1, ord("a"), ord("A"), ord("0"), ord(" ")) if 0 <= x < 0xD800 and x != c]
    if kind == "float":
        return [v for v in (value + 1.0, value - 1.0, 0.0, -value, value / 2) if v != value]
    return []


def mutations(ty: tuple, value: Any) -> list[Any]:
    """Single-step changes of one value, used to perturb I/O cases."""
    kind = ty[0]
    if kind in ("ref", "box"):
        return mutations(ty[1], value)
    if is_scalar(ty):
        return scalar_variants(ty, value)
    if kind in ("vec", "slice", "seq") and isinstance(value, list):
        out = []
        if value:
            out += [value[:-1], value[1:], [], list(reversed(value))]
            out.append(value + [value[-1]])
            for i in range(min(len(value), 4)):
                for v in mutations(ty[1], value[i])[:3]:
                    out.append(value[:i] + [v] + value[i + 1:])
        else:
            out += [[default_value(ty[1])], [default_value(ty[1])] * 2]
            out += [[v] for v in mutations(ty[1], default_value(ty[1]))[:3]]
        return out
    if kind == "array" and isinstance(value, list):
        out = []
        for i in range(min(len(value), 4)):
            for v in mutations(ty[1], value[i])[:3]:
                out.append(value[:i] + [v] + value[i + 1:])
        return out
    if kind in ("string", "str") and isinstance(value, str):
        out = [value[:-1], value[1:], "", value + "a"] if value else ["a", "A", " ", "ab"]
        for i in range(min(len(value), 3)):
            for v in scalar_variants(("char",), value[i])[:3]:
                out.append(value[:i] + v + value[i + 1:])
        return out
    if kind == "option":
        inner = default_value(ty[1]) if value is None else value
        return ([inner] if value is None else [None]) + [m for m in mutations(ty[1], inner)[:4]]
    if kind == "tuple" and isinstance(value, (list, tuple)):
        out = []
        for i, t in enumerate(ty[1]):
            for v in mutations(t, value[i])[:4]:
                out.append(list(value[:i]) + [v] + list(value[i + 1:]))
        return out
    if kind == "struct" and isinstance(value, (list, tuple)):
        out = []
        for i, (_, t) in enumerate(ty[2]):
            for v in mutations(t, value[i])[:4]:
                out.append(list(value[:i]) + [v] + list(value[i + 1:]))
        return out
    if kind == "enum":
        return [v for v in ty[2] if v != value]
    return []


def length_extremes(ty: tuple) -> list[Any]:
    """Length-only values beyond what a literal list can spell out."""
    base = ty[1] if ty[0] == "ref" else ty
    if base[0] in ("vec", "slice"):
        return [{"len": INT_BOUNDS["usize"][1]}, {"len": INT_BOUNDS["usize"][1] - 1}]
    return []


def load_suite(task_reference: str) -> list[dict]:
    """The task's frozen I/O cases (data/io), in the release's normalized form."""
    io_cases.set_io_suite_dir(str(ROOT / "data/io"))
    try:
        suite = io_cases.load_offline_io_suite(task_reference)
    except Exception:
        return []
    return list((suite or {}).get("cases") or [])


def mechanical_candidates(lemma: Lemma, cases: list[dict]) -> list[dict]:
    """Literal assignments from the task's I/O cases, their one-step perturbations and boundaries."""
    registry = registry_for(lemma)
    types = {slot: parse_type(info["type"], registry) for slot, info in lemma.slots.items()}
    order = {"L1": ("positive", "invalid", "negative"), "L2": ("negative", "positive", "invalid")}[lemma.direction]
    seeds: list[dict] = []
    for kind in order:
        for case in cases:
            if case.get("kind") != kind:
                continue
            inputs = case.get("inputs") or {}
            output = case.get("output") or case.get("mutated_output") or {}
            if not isinstance(output, dict):
                output = {}
            seeds.append(to_assignment(lemma, inputs, output, output))
    defaults = {slot: default_value(t) for slot, t in types.items()}
    seeds.append(dict(defaults))
    pool: list[dict] = []
    seen: set[str] = set()

    def bindable(slot: str, value: Any) -> bool:
        try:
            pins(slot, types[slot], value)
            return True
        except (LiteralError, KeyError, TypeError, IndexError):
            return False

    def add(candidate: dict):
        candidate = {s: v for s, v in candidate.items() if s in types and bindable(s, v)}
        full = {**defaults, **candidate}
        for slot, info in lemma.slots.items():          # unchanged &mut: post defaults to pre
            if info["role"] == "input" and info.get("mutable") and slot not in candidate:
                old = next((s for s, i in lemma.slots.items() if i["role"] == "old" and i["name"] == info["name"]), None)
                if old in candidate:
                    full[slot] = candidate[old]
        key = json.dumps(full, sort_keys=True, default=str)
        if key not in seen and len(pool) < POOL_CAP:
            seen.add(key)
            pool.append(full)

    for seed in seeds:
        add(seed)
    perturbed = []
    for seed in seeds:
        full = {**defaults, **seed}
        per_seed = []
        for slot, ty in types.items():
            for v in mutations(ty, full.get(slot)):
                per_seed.append({**full, slot: v})
        perturbed.append(per_seed)
    for group in itertools.zip_longest(*perturbed):
        for candidate in group:
            if candidate is not None:
                add(candidate)
    for slot, ty in types.items():
        for v in length_extremes(ty):
            add({**defaults, slot: v})
    return pool


class _ScoreTimeout(Exception):
    pass


def _quantifier_binders(text: str) -> int:
    return sum(len([b for b in m.split(",") if b.strip()]) for m in re.findall(r"\b(?:forall|exists)\s*\|([^|]*)\|", text))


SCORE_BUDGET_SECONDS = 3.0


def rank(lemma: Lemma, candidates: list[dict]) -> list[int]:
    """Candidate order for screening. Python scoring has a hard time budget; the rest rank as unknown."""
    import signal
    scores = [1] * len(candidates)

    def expire(signum, frame):
        raise _ScoreTimeout()

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, SCORE_BUDGET_SECONDS)
    try:
        for index, candidate in enumerate(candidates):
            scores[index] = python_score(lemma, candidate)
    except _ScoreTimeout:
        pass
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    return sorted(range(len(candidates)), key=lambda i: -scores[i])


def python_score(lemma: Lemma, assignment: dict) -> int:
    """Ranking only: 2 if the release's Python evaluator says the witness works, 1 unknown, 0 no."""
    def evaluate(call: str) -> Optional[bool]:
        wrapper = lemma.wrappers.get(call.split("(")[0])
        if wrapper is None or _quantifier_binders(wrapper.body) > 1:
            return None
        env = {}
        for name, _type, argument in wrapper.params:
            if argument not in assignment or is_length_only(assignment[argument]):
                return None
            env[name] = assignment[argument]
        try:
            return ce.eval_contract_expr(wrapper.body, env)
        except _ScoreTimeout:
            raise
        except Exception:
            return None
    values = [evaluate(c) for c in lemma.antecedent]
    consequent = [evaluate(c) for c in lemma.consequent]
    if False in values or (consequent and all(v is True for v in consequent)):
        return 0
    if all(v is True for v in values) and False in consequent:
        return 2
    return 1


def scalar_pair(ty: tuple) -> Optional[tuple[str, str]]:
    """Two literals of a type, used to build a value that differs from an unknown one."""
    if ty[0] == "int":
        return int_literal(0, ty[1]), int_literal(1, ty[1])
    if ty[0] == "float":
        return float_literal(1.0, ty[1]), float_literal(2.0, ty[1])
    if ty[0] == "bool":
        return "true", "false"
    return None


def read_slots(lemma: Lemma) -> list[str]:
    """Collection parameters that the clauses index into, consequent first."""
    out: list[str] = []
    for call in (*lemma.consequent, *lemma.antecedent):
        wrapper = lemma.wrappers.get(call.split("(")[0])
        for name, _, argument in (wrapper.params if wrapper else []):
            if argument in lemma.slots and argument not in out and re.search(rf"\b{re.escape(name)}@?\[", wrapper.body):
                out.append(argument)
    return out


def computed_candidates(lemma: Lemma, pool: list[dict]) -> list[dict]:
    """Literal seeds with one scalar replaced by a value built from an out-of-bounds read."""
    registry = registry_for(lemma)
    types = {slot: parse_type(info["type"], registry) for slot, info in lemma.slots.items()}

    def unref(ty: tuple) -> tuple:
        return unref(ty[1]) if ty[0] in ("ref", "box") else ty

    def seqs(slot: str) -> Optional[tuple]:
        ty = unref(types[slot])
        return ty[1] if ty[0] in ("vec", "slice", "seq") else None

    seeds = [seed for seed in pool if not any(is_length_only(v) for v in seed.values())]
    seeds.sort(key=lambda seed: sum(len(v) for v in seed.values() if isinstance(v, list)))
    out, seen = [], set()
    for seed in seeds:
        for read in read_slots(lemma):
            elem, value = seqs(read), seed.get(read)
            pair = scalar_pair(elem) if elem and is_scalar(elem) else None
            if pair is None or not isinstance(value, list):
                continue
            view = read if types[read][0] == "seq" else f"{read}@"
            for index in dict.fromkeys((len(value), -1)):
                term = f"{view}[{index}]"
                values = (term, f"if {term} == {pair[0]} {{ {pair[1]} }} else {{ {pair[0]} }}")
                for slot in types:
                    target = unref(types[slot])
                    if slot == read:
                        continue
                    for computed in values:
                        leaf = {"computed": computed}
                        if target == elem:
                            candidate = {**seed, slot: leaf}
                        elif seqs(slot) == elem:
                            candidate = {**seed, slot: [leaf, *(seed.get(slot) or [])[1:]]}
                        else:
                            continue
                        key = json.dumps(candidate, sort_keys=True, default=str)
                        if key not in seen and len(out) < COMPUTED_CAP:
                            seen.add(key)
                            out.append(candidate)
    return out


def model_candidates(lemma: Lemma, proposals: dict) -> list[dict]:
    """Hand-written literal values (this session's model tier), keyed by lemma key or sample|function|direction."""
    out = []
    for key in (lemma.key, f"{lemma.sample}|{lemma.function}|{lemma.direction}|{lemma.check}",
                f"{lemma.sample}|{lemma.function}|{lemma.direction}"):
        for proposal in proposals.get(key, []):
            out.append(to_assignment(lemma, proposal.get("inputs") or {}, proposal.get("post") or {},
                                     proposal.get("output") or {}))
    return out


# --------------------------------------------------------------------------- search and verdicts

def screen(lemma: Lemma, candidates: list[dict], rlimit: float = SCREEN_RLIMIT,
           log: Optional[list] = None) -> list[int]:
    """Indices of candidates whose witness fn verified inside one batch file (screening only)."""
    log = log if log is not None else []
    items, ranges, indices = [], [], []
    for index, candidate in enumerate(candidates):
        try:
            items.append(witness_fn(lemma, candidate, f"__wit_screen_{index}_x"))
            indices.append(index)
        except LiteralError:
            continue
    if not items:
        log.append({"bound": 0})
        return []
    text = file_with(lemma, items)
    for index, item in zip(indices, items):
        start = text.index(f"proof fn __wit_screen_{index}_x")
        first = text.count("\n", 0, start) + 1
        ranges.append((index, first, first + item.count("\n")))
    run = run_verus(text, "__wit_screen_*", rlimit=rlimit, timeout=30 + 6 * len(items))
    log.append({"bound": len(items), "verified": run.verified, "errors": run.errors, "timeout": run.timeout,
                "seconds": round(run.seconds, 3),
                "frontend_failed": not run.timeout and run.verified == 0 and run.errors == 0,
                "frontend_excerpt": re.findall(r"error[^\n]*", run.stderr)[:3]
                if not run.timeout and run.verified == 0 and run.errors == 0 else []})
    if run.timeout:
        return []
    bad = failed_lines(run.stderr)
    if run.errors == 0 and run.verified == 0:          # frontend failure: isolate the bad candidate
        if len(indices) > 1:
            half = len(indices) // 2
            left = screen(lemma, [candidates[i] for i in indices[:half]], rlimit, log)
            right = screen(lemma, [candidates[i] for i in indices[half:]], rlimit, log)
            return [indices[:half][i] for i in left] + [indices[half:][i] for i in right]
        return []
    if run.verified == 0:
        return []
    return [index for index, first, last in ranges if not any(first <= line <= last for line in bad)]


def confirm(lemma: Lemma, assignment: dict, evidence: Optional[Path]) -> dict:
    """Standalone witness run plus the assert(false) control."""
    text = file_with(lemma, [witness_fn(lemma, assignment, "__witness_main")])
    main = run_verus(text, "__witness_main", rlimit=CONFIRM_RLIMIT, timeout=120,
                     keep=evidence / "witness.rs" if evidence else None)
    result = {"witness_verified": positive(main), "witness_seconds": round(main.seconds, 3)}
    if not positive(main):
        result["verdict"] = None
        result["failure"] = "timeout" if main.timeout else "not_verified"
        return result
    control_text = file_with(lemma, [witness_fn(lemma, assignment, "__witness_main", control=True)])
    control = run_verus(control_text, "__witness_main", rlimit=CONFIRM_RLIMIT, timeout=120,
                        keep=evidence / "control.rs" if evidence else None)
    result["control_seconds"] = round(control.seconds, 3)
    # The control must reach verification and fail on assert(false) and nothing else.
    control_ok = (not control.timeout and control.verified == 0 and control.errors >= 1
                  and "assertion failed" in control.stderr)
    result["control_verified"] = positive(control)
    result["control_clean_failure"] = control_ok
    if positive(control) or not control_ok:
        result["verdict"] = None
        result["failure"] = "void_control_verified" if positive(control) else "control_inconclusive"
        return result
    result["verdict"] = "refuted"
    return result


def realize(lemma: Lemma, assignment: dict, evidence: Optional[Path]) -> dict:
    """Build the witness values with exec code, verify the same formulas about them, compile and run."""
    if any(computed_leaves(assignment)):
        return {"realized": None, "reason": "computed value, no single concrete input"}
    registry = registry_for(lemma)
    lets, args = [], {}
    try:
        for pname, ptype in lemma.params:
            ty = parse_type(ptype, registry)
            if pname not in assignment:
                return {"realized": None, "reason": f"unbound parameter {pname}"}
            value = assignment[pname]
            local = f"__v_{pname.strip('_')}"
            if ty[0] == "ref" and ty[1][0] == "slice":
                lets.append(f"    let {local}_own: Vec<_> = {exec_literal(('vec', ty[1][1]), value)};")
                lets.append(f"    let {local}: {ptype} = {local}_own.as_slice();")
            elif ty[0] == "ref":
                lets.append(f"    let {local}_own = {exec_literal(ty[1], value)};")
                lets.append(f"    let {local}: {ptype} = &{local}_own;")
            elif ty[0] == "str":
                lets.append(f"    let {local}: &str = {exec_literal(ty, value)};")
            else:
                lets.append(f"    let {local}: {ptype} = {exec_literal(ty, value)};")
            args[pname] = local
    except LiteralError as exc:
        reason = str(exc)
        return {"realized": False if reason.startswith("unrepresentable") else None, "reason": reason}

    def substitute(call: str) -> str:
        name, rest = call.split("(", 1)
        inner = rest.rsplit(")", 1)[0]
        return f"{name}({', '.join(args.get(a.strip(), a.strip()) for a in split_top(inner))})"

    literals = sorted(set(re.findall(r'"(?:[^"\\]|\\.)*"', "\n".join(lets))))
    body = ["fn __realize()", "{"] + lets
    body += [f"    proof {{ reveal_strlit({literal}); }}" for literal in literals]
    body += [f"    proof {{ {line.strip()} }}" for line in recursive_reveals(lemma, fuel_for(assignment))]
    # The proof witness's pins, re-proved about the exec values. They follow from the constructors
    # and give the solver the same element terms the proof witness had.
    for pname, ptype in lemma.params:
        for clause in pins(pname, parse_type(ptype, registry), assignment[pname]):
            body.append(f"    assert({re.sub(rf'(?<![A-Za-z0-9_]){re.escape(pname)}(?![A-Za-z0-9_])', args[pname], clause)});")
    body += [f"    assert({substitute(c)});" for c in lemma.antecedent]
    body += [f"    assert(!({' && '.join(substitute(c) for c in lemma.consequent)}));", "}"]
    # Realization targets this machine (x86_64), so the word size is stated for the exec file only.
    text = file_with(lemma, ["\n".join(body)], main_body="__realize();", prefix="global size_of usize == 8;")
    with tempfile.TemporaryDirectory(prefix="realize_") as tmp:
        exe = Path(tmp) / "witness_bin"
        if evidence:
            (evidence / "realize.rs").write_text(text)
        path = Path(tmp) / "realize.rs"
        path.write_text(text)
        cmd = [VERUS, "--crate-type=bin", "--verify-root", "--verify-function", "__realize", "--compile",
               "--rlimit", str(CONFIRM_RLIMIT), "--num-threads", "1", "-o", str(exe), str(path)]
        started = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return {"realized": None, "reason": "compile timeout"}
        finally:
            TIMING["verus_seconds"] += time.monotonic() - started
            TIMING["verus_runs"] += 1
        if proc.returncode != 0 or not exe.exists():
            tail = re.findall(r"error[^\n]*", proc.stderr)[:3]
            return {"realized": None, "reason": "exec witness did not verify or compile", "errors": tail}
        try:
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return {"realized": None, "reason": "run timeout"}
        if ran.returncode != 0:
            return {"realized": False, "reason": f"run failed with code {ran.returncode}", "stderr": ran.stderr[-500:]}
    return {"realized": True, "reason": "exec values verified, compiled and ran"}


def search(lemma: Lemma, cases: list[dict], proposals: dict, evidence_root: Optional[Path],
           realize_witness: bool = True, propagated: Optional[list[dict]] = None) -> dict:
    """Try proposers in order, stop at the first verdict."""
    record = {"key": lemma.key, "sample": lemma.sample, "function": lemma.function, "direction": lemma.direction,
              "form": lemma.form, "check": lemma.check, "release_status": lemma.release_status,
              "release_reason": lemma.release_reason, "verdict": None, "tier": None, "witness": None}
    started = time.monotonic()
    if lemma.harness is None:
        record["outcome"] = "no_harness"     # trivial shortcut, binding issue or frontend failure
        return record
    registry = registry_for(lemma)
    types = {n: parse_type(t, registry) for n, t in lemma.params}
    classes = set().union(*(type_class(t) for t in types.values())) if types else set()
    if any(info["role"] == "old" for info in lemma.slots.values()):
        classes.add("&mut/old")
    if recursive_reveals(lemma, FUEL_MIN):
        classes.add("recursive spec fn")
    record["type_classes"] = sorted(classes)
    if lemma.generic_parameters.strip() or any(contains_unsupported(t) for t in types.values()):
        record["outcome"] = "unsupported_type"
        return record
    evidence = None
    if evidence_root:
        evidence = evidence_root / hashlib.sha256(lemma.key.encode()).hexdigest()[:16]
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "key.txt").write_text(lemma.key + "\n")
    tiers = [("propagated", list(propagated or []))] if propagated else []
    tiers += [("model", model_candidates(lemma, proposals))] if proposals else []
    mechanical = mechanical_candidates(lemma, cases)
    tiers.append(("io_and_boundary", mechanical))
    tiers.append(("computed", computed_candidates(lemma, mechanical)))
    attempts = 0
    for tier, candidates in tiers:
        if not candidates:
            continue
        ranked = range(len(candidates)) if tier == "computed" else rank(lemma, candidates)
        batch = [candidates[i] for i in ranked[:COMPUTED_CAP if tier == "computed" else SCREEN_BATCH]]
        attempts += len(batch)
        hits = screen(lemma, batch, log=record.setdefault("screens", []))
        hits.sort(key=lambda i: any(is_length_only(v) for v in batch[i].values()))
        for hit in hits[:3]:
            outcome = confirm(lemma, batch[hit], evidence)
            if outcome["verdict"] == "refuted":
                record.update(verdict="refuted", tier=tier, witness=batch[hit], confirmation=outcome,
                              computed=any(computed_leaves(batch[hit])),
                              assumes_64bit_usize=assumes_64bit(lemma, batch[hit]))
                if realize_witness:
                    record["realization"] = realize(lemma, batch[hit], evidence)
                break
            record.setdefault("rejected_hits", []).append(outcome)
        if record["verdict"]:
            break
    record["candidates_tried"] = attempts
    record["outcome"] = record["verdict"] or "undecided"
    record["seconds"] = round(time.monotonic() - started, 3)
    return record


# --------------------------------------------------------------------------- command line

def main() -> None:
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", type=Path, default=Path.cwd(), help="VerusEval release root")
    parser.add_argument("--jobs", type=Path, required=True,
                        help="JSONL with sample, generated, reference, task_reference, function, directions, forms")
    parser.add_argument("--proposals", type=Path, help="JSONL of hand-written literal witnesses")
    parser.add_argument("--evidence", type=Path, help="keep witness and control files here")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-realize", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    ROOT = args.release.resolve()
    for name in ("jobs", "proposals", "evidence", "out"):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    os.chdir(ROOT)
    release_imports()
    proposals: dict[str, list] = {}
    if args.proposals:
        for line in args.proposals.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                proposals.setdefault(item["key"], []).append(item)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    jobs = [json.loads(line) for line in args.jobs.read_text().splitlines() if line.strip()]
    done = set()
    if args.out.exists():
        for line in args.out.read_text().splitlines():
            done.add(json.loads(line).get("job_id"))
    todo = [(job, proposals, args.evidence, not args.no_realize) for job in jobs
            if job_id(job) not in done]
    totals = {"verus_seconds": 0.0, "verus_runs": 0, "wall_seconds": 0.0}
    with args.out.open("a") as stream:
        if args.workers > 1:
            from multiprocessing import Pool
            with Pool(args.workers, initializer=_init_worker, initargs=(str(ROOT),)) as pool:
                results = pool.imap_unordered(run_job, todo)
                for records, timing in results:
                    for record in records:
                        stream.write(json.dumps(record, default=str) + "\n")
                    stream.flush()
                    for k in totals:
                        totals[k] += timing.get(k, 0)
        else:
            for item in todo:
                records, timing = run_job(item)
                for record in records:
                    stream.write(json.dumps(record, default=str) + "\n")
                stream.flush()
                for k in totals:
                    totals[k] += timing.get(k, 0)
    print(json.dumps(totals))


def job_id(job: dict) -> str:
    return hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()[:16]


def _init_worker(root: str) -> None:
    global ROOT
    ROOT = Path(root)


def run_job(item) -> tuple[list[dict], dict]:
    job, proposals, evidence, realize_witness = item
    if "li" not in globals():
        release_imports()
    TIMING["verus_seconds"], TIMING["verus_runs"] = 0.0, 0
    started_job = time.monotonic()
    cases = load_suite(job["task_reference"])
    meta = {k: job[k] for k in job if k not in ("generated", "reference", "task_reference")}
    records = []
    found: dict[str, dict] = {}     # guarded witnesses by clause index, tried first on the unconditional lemma
    for direction in job.get("directions", ["L1", "L2"]):
        forms = ["single"] if direction == "L1" else sorted(job.get("forms", ["unconditional"]),
                                                             key=lambda f: f != "guarded")
        for form in forms:
            started = time.monotonic()
            try:
                lemmas = capture(job["sample"], job["generated"], job["reference"], job["function"],
                                 direction, "unconditional" if form == "single" else form)
            except Exception as exc:
                records.append({**meta, "direction": direction, "form": form, "outcome": "capture_error",
                                "error": f"{type(exc).__name__}: {exc}"})
                continue
            capture_seconds = time.monotonic() - started
            for lemma in lemmas:
                lemma.form = form
                lemma.key = f"{lemma.sample}|{lemma.function}|{direction}|{form}|{lemma.check}"
                if job.get("only_status") and lemma.release_status not in job["only_status"]:
                    records.append({**meta, "key": lemma.key, "direction": direction, "form": form,
                                    "check": lemma.check, "release_status": lemma.release_status,
                                    "verdict": None, "outcome": "not_searched"})
                    continue
                index = lemma.check[-3:]
                carry = [found[index]] if form == "unconditional" and index in found else None
                try:
                    record = search(lemma, cases, proposals, evidence, realize_witness, carry)
                    if form == "guarded" and record.get("verdict") == "refuted":
                        found[index] = record["witness"]
                except Exception as exc:
                    record = {"key": lemma.key, "direction": direction, "form": form, "check": lemma.check,
                              "release_status": lemma.release_status, "verdict": None,
                              "outcome": "engine_error", "error": f"{type(exc).__name__}: {exc}"}
                record.update({k: v for k, v in meta.items() if k not in record})
                record["capture_seconds_shared"] = round(capture_seconds, 3)
                records.append(record)
            if not lemmas:
                records.append({**meta, "direction": direction, "form": form, "outcome": "no_lemmas"})
    for record in records:
        record["job_id"] = job_id(job)
    return records, {"verus_seconds": TIMING["verus_seconds"], "verus_runs": TIMING["verus_runs"],
                     "wall_seconds": time.monotonic() - started_job}


if __name__ == "__main__":
    main()
