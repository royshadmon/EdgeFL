Created memory file [](file:///Users/juan/Library/Application%20Support/Code/User/workspaceStorage/2886748dfe63723967388ba27e44a41d/GitHub.copilot-chat/memory-tool/memories/ZGI3MWM5NzQtYzFhMi00NDM1LTg3ZjEtYWM1Y2U0NWRmMmNh/plan.md)

Deleted memory [](file:///Users/juan/Library/Application%20Support/Code/User/workspaceStorage/2886748dfe63723967388ba27e44a41d/GitHub.copilot-chat/memory-tool/memories/ZGI3MWM5NzQtYzFhMi00NDM1LTg3ZjEtYWM1Y2U0NWRmMmNh/plan.md)

Created memory file [](file:///Users/juan/Library/Application%20Support/Code/User/workspaceStorage/2886748dfe63723967388ba27e44a41d/GitHub.copilot-chat/memory-tool/memories/ZGI3MWM5NzQtYzFhMi00NDM1LTg3ZjEtYWM1Y2U0NWRmMmNh/plan.md)

## Plan: EdgeFL Benchmarking MVP (Master sqlite, long format)

Use a normalized long-format benchmarks table on the master sqlite DB (benchmarkfl.fl_benchmarks) and a single `record_metric` API in the Benchmarker so every metric writes rows with identical JSON keys. Step 1 (master sqlite DB/table) is already completed and verified; proceed with module changes and instrumentation.

**Steps**
1. Storage provisioning (done)
   1. benchmarkfl logical DB created on master with sqlite backing.
   2. fl_benchmarks table created and verified via get databases.

2. Update benchmarking module to long format (*depends on 1, already satisfied*)
   1. Benchmarker should expose a single `record_metric(training_index, round_number, node_name, metric_name, metric_value, timestamp=None)` that enqueues one row with consistent keys.
   2. Optionally keep convenience wrappers (`record_node_round_start`, `record_node_round_end`, `record_accuracy`, `record_agg_metrics`) but have them call `record_metric` with standardized `metric_name` values.
   3. Standard `metric_name` values for MVP:
      - `training_time_s`
      - `wait_time_s`
      - `aggregation_time_s`
      - `straggler_gap_s`
      - `accuracy`
   4. JSON row keys must always be: `training_index`, `round_number`, `node_name`, `metric_name`, `metric_value`, `timestamp`.
   5. Keep the background worker thread and `requests.Session`; only change payload shape.

3. Instrument node_server.py for node metrics (*depends on 2*)
   1. On round start (after round_data found, before `train_model_params`), compute `wait_time_s` from stored `last_round_end_ts` or node init time and call `record_metric` with `metric_name=wait_time_s`.
   2. On round end (after `add_node_params`), compute `training_time_s` and call `record_metric` with `metric_name=training_time_s`.
   3. After publish, spawn a daemon thread to run `node_instance.inference` and record accuracy with `metric_name=accuracy`.

4. Instrument aggregator_server.py for aggregation and straggler metrics (*depends on 2*)
   1. Track `first_node_policy_ts` and `last_node_policy_ts` in `listen_for_update_agg`.
   2. Immediately before and after `aggregate_model_params`, compute `aggregation_time_s` and `straggler_gap_s` and record them with `node_name=agg`.

5. Data flow diagram (*parallel with steps 2-4 for documentation*)
   Node/agg metric capture -> `Benchmarker.record_metric` -> queue -> worker thread -> master REST PUT -> benchmarkfl sqlite file

**Relevant files**
- benchmarker.py — normalize payload to long format and central `record_metric`.
- __init__.py — package init for imports.
- node_server.py — add calls for `wait_time_s`, `training_time_s`, `accuracy`.
- aggregator_server.py — add calls for `aggregation_time_s` and `straggler_gap_s`.
- node.py — inference entry point used by async accuracy worker.
- custom_data_handler.py — accuracy computation.

**Verification**
1. Insert a small run and query fl_benchmarks on the master for each `metric_name` to confirm rows are stored.
2. Validate `wait_time_s` and `training_time_s` values for each node and round.
3. Validate `aggregation_time_s` and `straggler_gap_s` values for each round (`node_name=agg`).
4. Confirm accuracy rows appear per node per round and that node listeners continue without delay.

**Decisions**
- Use long/normalized schema with one metric per row and a single `record_metric` API.
- Store benchmark rows in master sqlite benchmarkfl (step 1 completed).

**Further Considerations**
1. SQLite single-writer bottleneck remains acceptable for MVP; keep REST target configurable for later Postgres migration.
2. Ensure master sqlite file is on a durable volume to avoid data loss.
3. Log resolved REST target on startup to avoid writing to an operator by mistake.

If you want any tweaks, tell me what to adjust and I’ll update the plan.
