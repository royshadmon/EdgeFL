# Benchmarking feature README (WIP)

## General idea
- To send all benchmarks to a single node for scaling purposes.
- Receiving node has a daemon thread receiving the metrics and sending them to a specific db.
- Benchmarking process only runs if `BENCMARK_ENABLED` is set in all env files.

## Current state of feature
1. Send metrics from all operators into operator1, then save the metric into `benchmarkfl` sqlite db.
2. Query the metrics from operator1 with `sql benchmarkfl "select * from fl_benchmarks where ..."` 
3. Visualize the stored data using `visualizer.py`.
4. Toggle benchmarking on/off through an environment variable.

**Implemented metrics:**
- [x] `training_time_s` -> Time spent training in each round.
- [x] `polling_time_s` -> Time spent polling in each round.
- [x] `total_round_time_s` -> Time it took to complete this round.
- [ ] `round_accuracy` -> Accuracy for this round.
    - Pending to reuse Ivan's code post-integration.
- [x] `aggregation_time` -> Time spent aggregating this round. 

### Steps to reproduce
1. In the environment files for the 3 operators add:
```
# Address for benchmarking module, set to point to operator1 node
BENCHMARK_REST_CONN="127.0.0.1:32149"
BENCHMARK_ENABLED="True"
```

2. Spin up anylog and attach to operator1
3. Run some round of training (ingest data, spin up the node servers, use gui...)
4. In the operator1, run `sql benchmarkfl "select * from fl_benchmarks"`, we should see a list containing one json entry per node per round.
```
AL operator1 +> sql benchmarkfl "select count(*) from fl_benchmarks where round_number = 1"

{"Query":[{"count(*)":12}],
"Statistics":[{"Count": 1,
                "Time":"00:00:00",
                "Nodes": 1}]}
```

## Known issues
- **`initialize_training_app_on_index` no longer guards against load failures.** During the
  accuracy/rollback integration, Ivan's branch removed the `try/except` that previously
  wrapped the training-app load in `node.py:initialize_training_app_on_index` (it used to
  return a `{'status': 'error', ...}` dict on failure). We accepted his version, so a failure
  while loading the training application for an index now propagates out of `/init-node`
  instead of being logged and swallowed. This conflicts with the project rule that the
  software should never stop on random errors — revisit if init-time crashes appear.
