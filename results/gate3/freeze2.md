# Second freeze record

Verus 0.2025.09.25.04e8687, Rust 1.88.0, image `veruseval:haiku`. Grader models: claude-haiku-5-5 and claude-sonnet-5-5 through the Batches API, one try each, 12,000 max tokens. RQ4 subject: claude-haiku-5-5 through the StarVerus few-shot adapter, one run per task, in a full arm and a bare arm. RQ5 subject: the same model, bare, in four arms, few-shot and zero-shot, with and without task text, one run per task and arm. Both use the API key.

`freeze-1` froze revision 6. Between the two, the paper's question changed and these were added: `part_a.py`, `task_text.py`, `rq5_labels.py`, the RQ5 table in `census_report.py`, the `--text` option in `rq4_generate.py`, and `rq5_tasks.txt`. The grader files `witness.py`, `gate2_check.py`, `tier_batch.py`, `gate2_regenerate.py` and `gate2_tier0.py` did not change.

Runs made before this freeze: the census pipeline on development clauses, the contract variants, 14 of the 30 regrade artifacts, and released labels for Part A. No census task has gone through the grader as a natural obligation, apart from those 14.

File hashes are in `freeze2.sha256`. Check them with `sha256sum -c results/gate3/freeze2.sha256`. Any later change to these files is a logged deviation, and the affected tier is re-run.
