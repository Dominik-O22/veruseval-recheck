# VeruSteer re-check

A re-check of [VeruSteer: Learning What to Repair Next in Verus](https://arxiv.org/abs/2610.29755) (Jiang, Wang et al., 2026), the same group's follow-up to VerusEval, built on the authors' released artifact ([lifetruthuu/VeruSteer](https://github.com/lifetruthuu/VeruSteer), commit `ce17fd3`). The artifact reproduces the paper's numbers exactly.

VeruSteer plugs into the AutoVerus and VeruSAGE repair pipelines. When Verus reports several error types, the pipeline repairs one per round, chosen by a fixed priority list. VeruSteer learns that choice instead and raises verified test trees from 185 to 194 of 1,270, which is 14.6% to 15.3%.

The question here: why do 85% of repairs fail, and does a current agent that can run Verus itself do better on the same inputs?

## Findings

**1. Most failures cannot be fixed under the pipelines' own rules.** The repair may only change proof code. A checker called lynette rejects any candidate that changes executable code, `requires`/`ensures`, function `decreases` or imports. That's a sensible rule when a human wrote the contract. Here DeepSeek-Chat and Qwen3-Coder wrote it, and 972 of the 1,270 test programs don't compile at the start. For every failing program, [`scripts/frozen_check.py`](scripts/frozen_check.py) deletes everything the repair may change, confirms lynette still sees the result as unchanged, and compiles it. If that fails, no allowed edit can make the program compile.

744 of the 1,085 failures are unfixable this way, 69%, and up to 15 more are uncertain. None of the 185 programs the pipeline did verify lands in an unfixable bucket. The most common blockers are type errors inside contracts, an import that doesn't exist (`use vstd::vec::*`, 98 programs), triggers Verus can't infer in an `ensures` (68), and executable code written inside `proof { }`.

That count is a floor. The 30-task sample below was drawn only from failures the classifier rated possibly fixable. Reading every result showed 8 of the 30 blocked by the rules anyway, 10 with contracts that are false or unprovable as written, and 1 unclear. 11 were really fixable, counting one whose broken spec function the rules let a repair rewrite.

**2. Most failed runs never touch the program.** In 796 of 1,085 failed runs, 73%, the final program is byte-identical to the input after five rounds. In VeruSAGE's recorded trees, 98.7% of repair rounds on non-compiling programs keep the original. On one task we re-ran, the default rule sent all five rounds to a rule-based type fixer that never calls the model, reproducing the recorded trajectory error count for error count. [`results/trajectory_stats.txt`](results/trajectory_stats.txt) has these numbers.

**3. With the same inputs and the same model, an agent fixes more.** 30 failing test trees, half per pipeline, sampled from trees where every recorded repair path failed ([`scripts/sample_fixable.py`](scripts/sample_fixable.py)). Each result counts only if Verus verifies it and it passes that tree's own lynette check. The agents got the pipeline's rules in their prompt and were told to write `UNPROVABLE.md` with a counterexample if the contract is false.

| | Their pipeline, recorded (DeepSeek-Chat) | Their pipeline + Haiku 5.5 | Haiku 5.5 agent | DeepSeek V4.1 Flash agent |
|---|---|---|---|---|
| Accepted, of 30 | 0 | 6 | 10 | 9 |
| Accepted, of the 11 fixable | 0 | 6 | 10 | 9 |
| Contracts reported false or unprovable, with a reason | 0 | 0 | 9 | 10 |
| Model cost for all 30 | | $0.39 | $1.57 | free |
| Median time per task | | 79 s | 38 s | 90 s |

The recorded zero comes from how the sample was drawn, so the comparison that matters is the middle two columns: same model, different workflow. Haiku ran through the pipeline via [`scripts/sdk_proxy.py`](scripts/sdk_proxy.py), an OpenAI-compatible endpoint, so their code runs unmodified. The agents are a Claude Agent SDK session and [opencode](https://opencode.ai) with its free DeepSeek model, both with a shell and Verus in the container.

The agents also flagged the broken contracts, which the pipeline has no way to do. DeepSeek wrote up all 10; Haiku wrote up 9 and explained the tenth when it stopped. On 9 tasks both agents independently found the same problem, often the same counterexample: Euclidean versus truncating `%` on negative numbers, `a * a` overflowing `u64`, aliased indices in a three-way swap, a `reverse_spec` that is the identity function. Several rejected agent repairs fixed what the generator obviously meant, such as moving an executable loop out of a `proof { }` block, but broke the rules doing so and are counted as failures. [`results/s30/verdicts.csv`](results/s30/verdicts.csv) has a hand verdict and a note for every task.

**4. The two gates differ, and both have a hole.** [`gate_examples/`](gate_examples) reproduces this table in a second ([`results/gates.txt`](results/gates.txt)):

| Edit | AutoVerus check | VeruSAGE check |
|---|---|---|
| add a loop invariant | allow | allow |
| add a proof fn | allow | allow |
| add an import | reject | allow |
| remove an import that does not resolve | reject | reject |
| rewrite a spec fn body to `true` | allow | reject |
| change exec code in an `if` whose `else` is proof-only | allow | allow |

AutoVerus's check ignores spec functions entirely, so rewriting `is_sorted` to `true` turns a sorting contract vacuous and the program verifies. In the 30-task run, the pipeline and both agents used that freedom on `VH0036`, where the generated spec function returns 0 for every input. All three rewrote it to count what the code counts, which matches the obvious intent but is still a contract change.

The last row is a lynette bug. An `if` whose `else` holds only proof code disappears from the program lynette compares, so changing `x = x + 1` to `x = 0` inside it passes both checks. I have not checked whether any recorded success went through it.

**5. The released VeruSAGE repair code crashes with its own example config.** Its config object raises `KeyError` instead of `AttributeError`, so `getattr(config, "fvt_mode", False)` throws whenever the key is missing, and the example config omits it. Every model-backed repair action then fails before calling the model, and the error handler fails too, because it passes a `success` argument `ActionResult` doesn't accept. [`scripts/run_pipeline.py`](scripts/run_pipeline.py) sets the missing keys to their intended defaults.

## What holds up

The artifact is careful. It reproduces 185 and 194 exactly and documents its own data anomalies. The contract freeze works as intended on their successes: 184 of 185 verified programs pass lynette against their starting program. VeruSteer's gain on the recorded trees is real, and the abstract reports it as the small number it is.

The problem is what it optimizes. Most failures are decided before the first round: the selector picks which error to repair in programs no allowed repair can fix. The obvious baseline, giving the model every diagnostic or a shell with Verus, is named in the paper's related work and never run.

## Caveats

- 30 tasks, one run per arm, no variance estimate.
- The false-contract verdicts are model claims I checked by reading, not by running Verus. On 9 of the 10, two independent agents agree.
- The agents read the rules from a prompt, while the pipeline enforces them in code. All four columns are graded by the same lynette checks, and verdicts.csv lists every case where a rule decided the outcome.
- Through the proxy, Haiku sees few-shot examples inlined into one message, and temperature isn't forwarded.
- The released repair implementation is not the code that recorded the trees; the authors call them distinct. Our re-run matched a recorded trajectory on one task.
- frozen_check.py models AutoVerus's check. VeruSAGE also freezes proof function signatures and spec functions, so its unfixable count is understated.

## Reproducing

You need the VeruSteer repository, podman, Rust/cargo, and for the model runs a Claude login (the scripts read the access token from `~/.claude/.credentials.json` and pass only that to the container) and opencode.

```bash
mkdir work && cp verusteer/scripts/*.py verusteer/Containerfile.* work/ && cd work
git clone https://github.com/lifetruthuu/VeruSteer && git -C VeruSteer checkout ce17fd3
(cd VeruSteer && cat downloads/corpus-00*.bin | tar -xzf - data/paths/test_autoverus.jsonl \
    data/paths/test_verusage.jsonl data/trees/verusage)
python3 -I extract_tests.py VeruSteer .        # test_trees.csv and roots/

# lynette with a skeleton mode that prints the frozen part of a program
cp -r VeruSteer/pipelines/repair/utils/lynette/source lynette
(cd lynette && patch -p1 < ../../verusteer/patches/lynette-skeleton.patch && cargo build --release)
python3 -I trajectory_stats.py VeruSteer lynette/target/release/lynette
sh ../verusteer/gate_examples/gates.sh $PWD/lynette/target/release/lynette

# Containers: veruseval:haiku comes from the Containerfile at the repository root
podman build -t veruseval:agent -f Containerfile.agent .
podman build -t veruseval:pipeline -f Containerfile.pipeline .
python3 -I frozen_check.py VeruSteer runs/frozen
python3 -I sample_fixable.py VeruSteer runs/frozen/frozen_check.csv runs/sample-30.csv

# Their pipeline needs its own copy with lynette built inside the container
mkdir -p pipe cargo-home && cp -r VeruSteer/pipelines/repair pipe/
podman run --rm -v $PWD/pipe:/pipe:Z -v $PWD/cargo-home:/cargo-home:Z -e CARGO_HOME=/cargo-home \
    veruseval:pipeline sh -c 'cd /pipe/repair/utils/lynette/source && cargo build'
python3 -I run_pipeline.py runs/sample-30.csv --out runs/pipeline-haiku
python3 -I run_agent.py run runs/sample-30.csv --model claude-haiku-5-5 --out runs/agent-haiku
python3 -I run_agent.py run runs/sample-30.csv --model opencode/deepseek-v4.1-flash-free --out runs/agent-deepseek
for run in pipeline-haiku agent-haiku agent-deepseek; do python3 -I run_agent.py grade runs/$run; done
```

Before building `veruseval:agent`, copy opencode's standalone linux-x64 binary to `work/opencode-bin`. In an npm or mise install it is `node_modules/@opencode/cli-linux-x64/bin/opencode`.

## Layout

- `scripts/`: test extraction, trajectory statistics, the unfixable classifier, the sampler, the agent and pipeline runners, the SDK proxy
- `patches/lynette-skeleton.patch`: adds a skeleton mode to lynette, which is MIT-licensed code from Microsoft's verus-proof-synthesis
- `gate_examples/`: small programs and a script that show what each check accepts
- `results/frozen_check.csv`: classifier status for every test tree
- `results/s30/`: the sample, grades per arm and the hand verdicts

VeruSteer's repository has no license, so its programs, and our repairs of them, are referenced by tree ID and not redistributed.
