"""Independent re-check of gate 2 verdicts. Does not import gate2_check.py.

For every clause with a regenerated harness, re-runs the claimed verdict with a separate splice and
template, and adds controls:
  proof:   same proof must verify; with assert(false) appended it must NOT (else the antecedent or
           context is contradictory, so the proof is vacuous).
  witness: every requires clause, parsed in full, must hold and the conjunction of ensures clauses
           must fail; asserting the un-negated consequent must NOT verify; assert(false) must NOT.
"""
import csv, json, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

H, P, CSV, OUT = Path("/g2run/harness"), Path("/repo/proofs/gate2"), Path("/repo/results/gate2/clauses.csv"), Path("/g2run/verify.jsonl")
VERUS = "/opt/verus/verus"
BAD = re.compile(r"\b(assume|admit|assume_specification)\b|external_body|#\[verifier|#!\[verifier|unsafe")


def verus(text, extra=()):
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "x.rs"
        f.write_text(text)
        try:
            r = subprocess.run([VERUS, "--crate-type=lib", *extra, str(f)], capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            return "timeout"
    log = r.stdout + r.stderr
    return "ok" if r.returncode == 0 and re.search(r"verification results:: [1-9]\d* verified, 0 errors", log) else "fail"


def parts(h):
    m = re.search(r"proof fn (lemma_sqm_\w+)", h)
    i = h.index("(", m.end())
    depth = 0
    for j in range(i, len(h)):
        depth += h[j] == "("
        depth -= h[j] == ")"
        if depth == 0:
            break
    o = h.index("{", j)
    c = h.index("}", o)
    head = h[j + 1:o]
    params = h[i + 1:j]
    def split(s):
        out, d, cur = [], 0, ""
        for ch in s:
            d += ch in "(<["
            d -= ch in ")>]"
            if ch == "," and d == 0:
                out.append(cur.strip()); cur = ""
            else:
                cur += ch
        return [x for x in out + [cur.strip()] if x]
    rq = re.search(r"\brequires\b(.*?)(\bensures\b|$)", head, re.S)
    en = re.search(r"\bensures\b(.*)$", head, re.S)
    return m.group(0), m.start(), o, c, split(params), split(rq.group(1)) if rq else [], split(en.group(1)) if en else []


def proof_files(name):
    text = (name).read_text()
    helpers, _, body = text.partition("// ---- body")
    return helpers, body


def check_proof(h, path):
    _, start, o, c, *_ = parts(h)
    if h[o + 1:c].strip():
        return {"proof": "lemma not empty"}
    helpers, body = proof_files(path) if path else ("", "")
    # Wrapper names carry a path-dependent hash, so map them to this machine's harness by base name.
    local = {re.sub(r"_[0-9a-f]{10}$", "", n): n for n in re.findall(r"__sqm_gen_\w+", h)}
    fix = lambda s: re.sub(r"__sqm_gen_\w+", lambda m: local.get(re.sub(r"_[0-9a-f]{10}$", "", m.group(0)), m.group(0)), s)
    helpers, body = fix(helpers), fix(body)
    if BAD.search(helpers + body):
        return {"proof": "forbidden"}
    build = lambda b: h[:start] + helpers.strip() + "\n\n" + h[start:o + 1] + "\n" + b + "\n" + h[c:]
    return {"proof": verus(build(body.strip()), ["--rlimit", "100"]),
            "false_control": verus(build(body.strip() + "\nassert(false);"), ["--rlimit", "100"])}


def check_witness(h, path):
    w = json.loads(path.read_text())
    _, _, _, _, params, req, ens = parts(h)
    fuel = "".join(f"reveal_with_fuel({k}, {v});\n" for k, v in w.get("_fuel", {}).items())
    types = w.get("_types", {})
    lets = []
    for p in params:
        n, t = [x.strip() for x in p.split(":", 1)]
        for k, v in types.items():
            t = re.sub(rf"\b{k}\b", v, t)
        ghost = "ghost " if re.match(r"^(int|nat|Seq<|Set<|Map<|spec_fn)", t) else ""
        if n not in w:
            return {"witness": f"no value for {n}"}
        lets.append(f"let {ghost}{n}: {t} = {w[n]};")
    def fn(asserts):
        return (h + "\nverus! {\n#[allow(unused_variables)]\nfn __check() {\n" + "\n".join(lets) + "\nproof {\n" + fuel
                + "\n".join(asserts) + "\n}\n}\n}\n")
    conj = " && ".join(f"({e})" for e in ens)
    flags = ["--verify-root", "--verify-function", "__check"]
    ant = [f"assert({r});" for r in req]
    return {"clauses_req": len(req), "clauses_ens": len(ens),
            "witness": verus(fn(ant + [f"assert(!({conj}));"]), flags),
            "unnegated_control": verus(fn(ant + [f"assert({conj});"]), flags),
            "false_control": verus(fn(ant + ["assert(false);"]), flags)}


def work(row):
    out = {"id": row["id"], "dir": row["direction"], "forms": row["forms"], "guarded": row["guarded"], "uncond": row["uncond"]}
    d = H / row["id"]
    if not d.exists():
        return {**out, "skip": "no harness"}
    p = P / row["id"]
    for form, claim in (("uncond", row["uncond"]), ("guarded", row["guarded"])):
        if form == "guarded" and row["forms"] == "one":
            continue
        harness = d / f"{form}.rs"
        if not harness.exists():
            out[form] = {"result": "no harness for form"}
            continue
        h = harness.read_text()
        try:
            if claim == "proved":
                out[form] = check_proof(h, (p / f"{form}.rs") if (p / f"{form}.rs").exists() else None)
            elif claim == "refuted":
                f = p / f"{form}.json"
                if not f.exists() and form == "guarded":
                    f = p / "uncond.json"
                out[form] = check_witness(h, f) if f.exists() else {"witness": "no file"}
            else:
                out[form] = {"result": "undecided"}
        except Exception as e:
            out[form] = {"error": repr(e)[:160]}
    return out


rows = list(csv.DictReader(CSV.open()))
with OUT.open("w") as s, ThreadPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as pool:
    for res in pool.map(work, rows):
        s.write(json.dumps(res) + "\n")
        s.flush()
print("done")
