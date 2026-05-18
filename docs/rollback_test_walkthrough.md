# EdgeFL — Rollback Test Walkthrough

**Centralized FL: 1 Aggregator · 3 Training Nodes · `minParams = 3`**  
**10 Rounds with Manual Rollback Triggered After Round 7**

> **Purpose:** This document traces every round of a 10-round federated learning run exactly as the current code executes it. It includes the state of the aggregator, all three training nodes, and the model weights at every step. A manual rollback is triggered on **Node 1 only** after round 7 produces a large drop in accuracy. Use this as a checklist when running the system to verify the rollback mechanism behaves as implemented.

---

## Table of Contents

1. [System Configuration](#1-system-configuration)
2. [Round Lifecycle (Code Flow)](#2-round-lifecycle-code-flow)
3. [Rounds 1–6: Normal](#3-rounds-16-normal)
4. [Round 7: The Bad Round](#4-round-7-the-bad-round)
5. [Triggering the Manual Rollback](#5-triggering-the-manual-rollback)
6. [Round 8: The Stale Round](#6-round-8-the-stale-round)
7. [Rounds 9–10: Recovery](#7-rounds-910-recovery)
8. [Full Accuracy Report: Expected Output](#8-full-accuracy-report-expected-output)
9. [Rollback History Endpoint](#9-rollback-history-endpoint)
10. [Test Verification Checklist](#10-test-verification-checklist)
11. [Quick Reference: All Curl Commands](#11-quick-reference-all-curl-commands)
12. [Note on Decentralized FL](#12-note-on-decentralized-fl)

---

## 1. System Configuration

| Parameter | Value |
|---|---|
| FL topology | Centralized (1 aggregator + 3 training nodes) |
| Index | `mnist` |
| `minParams` | 3 — aggregator waits for all 3 nodes every round |
| Total rounds | 10 |
| Rollback trigger | Manual via `POST /rollback` after round 7 |
| Rollback target | Round 6 (loads W_agg_6) |
| `ROLLBACK_ENABLED` | `true` |
| `ROLLBACK_AUTO_ENABLED` | `false` (manual only) |
| `ROLLBACK_PATIENCE_ROUNDS` | 3 |
| `ROLLBACK_ALLOW_MANUAL` | `true` |
| Node 1 port | 8080 |
| Node 2 port | 8081 |
| Node 3 port | 8082 |

### Key Model Weight Notation

- **W_agg_0** — random initial weights (used only in round 1, never explicitly named in policies).
- **W_agg_R** — the aggregated global model produced *after* round R completes. Written to `{R}-{agg_name}_update.json` on the aggregator.
- **`initParams` of `RoundStart(R)`** — always points to W_agg_(R-1). The node that downloads this is starting round R from the previous round's aggregated model.

### What `initial_accuracy` and `final_accuracy` Mean

| Field | Meaning |
|---|---|
| `initial_accuracy` (`global@node`) | Accuracy of W_agg_(R-1) on *this node's local test set*, measured **before** any local training. A drop here means the global model is generalising less well to this node's data distribution. |
| `final_accuracy` (`after_train`) | Accuracy **after** this node's local fine-tuning. |
| `contributed` | `after_train − global@node`. How much improvement this node added in this round. |
| `Δ_global` | Change in `global@node` vs the previous round. A sustained negative value is your rollback candidate signal. The report marks drops > 5% with `!`. |

---

## 2. Round Lifecycle (Code Flow)

Every round executes in the same sequence. Round 1 is slightly different because there are no prior aggregated weights.

```
┌─────────────────────────────────────────────────────────┐
│  AGGREGATOR                                             │
│  Publishes RoundStart(R)                                │
│  initParams = path to W_agg_(R-1)                       │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  EACH NODE                                              │
│  Finds RoundStart(R) on blockchain                      │
│  Downloads W_agg_(R-1) from initParams                  │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  EACH NODE                                              │
│  run_inference() → initial_accuracy                     │
│  (accuracy of W_agg_(R-1) on local test set)            │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  EACH NODE                                              │
│  train(R) → local fine-tuning                           │
│  run_inference() → final_accuracy                       │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  EACH NODE                                              │
│  Saves {R}-replica-{name}.pkl                           │
│  Publishes submodel policy to blockchain                │
│  Calls push_accuracy(R, init, final)                    │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  AGGREGATOR                                             │
│  Polls blockchain for minParams=3 submodel policies     │
│  Aggregates (FedAvg) → W_agg_R                          │
│  Publishes RoundStart(R+1) with initParams = W_agg_R    │
└─────────────────────────────────────────────────────────┘
```

### Round 1 Special Case

In round 1, the aggregator publishes `RoundStart(1)` with `initParams = ""` (empty string). Each node detects `round_number == 1 and not aggregator_model_params_db_link` and calls `get_weights()` to obtain random initial weights instead of downloading anything. `initial_accuracy` in round 1 is therefore approximately **10%** for 10-class MNIST — the model has not learned anything yet.

---

## 3. Rounds 1–6: Normal

> **Note on accuracy values:** The values below are representative for a 10-class MNIST run. Your exact numbers will differ, but the shape of the curve (rapid rise early, then diminishing returns) should match. Node 1 has a slightly harder data partition and converges more slowly.

| Round | Aggregator Action | Node 1 global | Node 1 train | Nodes 2&3 global (avg) | Nodes 2&3 train (avg) | Produces |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 1 | Publishes `RoundStart(1)`, `initParams=""` | 10.2% | 52.4% | 10.5% | 55.1% | W_agg_1 |
| 2 | `RoundStart(2)`, `initParams=W_agg_1` | 57.3% | 63.1% | 58.6% | 65.3% | W_agg_2 |
| 3 | `RoundStart(3)`, `initParams=W_agg_2` | 65.4% | 70.2% | 66.1% | 71.8% | W_agg_3 |
| 4 | `RoundStart(4)`, `initParams=W_agg_3` | 70.1% | 74.3% | 71.4% | 75.9% | W_agg_4 |
| 5 | `RoundStart(5)`, `initParams=W_agg_4` | 74.4% | 77.6% | 75.2% | 78.7% | W_agg_5 |
| 6 | `RoundStart(6)`, `initParams=W_agg_5` | **77.2%** | **80.1%** | **78.3%** | **81.4%** | W_agg_6 |

**What to observe in the logs (rounds 1–6):**

```
[mnist][Round 1] Listening for start round 1
[mnist][Round 1] Step 2 Complete: Model training done
[mnist][Round 1] Step 3 Complete: Model parameters published
[mnist][Round 1] Accuracy stored: initial=10.20%  final=52.40%  status=200
[mnist][Round 2] Listening for start round 2
...
[mnist][Round 6] Accuracy stored: initial=77.20%  final=80.10%  status=200
[mnist][Round 7] Listening for start round 7
```

---

## 4. Round 7: The Bad Round

Round 7 starts normally. The aggregator publishes `RoundStart(7)` with `initParams` pointing to W_agg_6. All three nodes download W_agg_6 and run inference.

| Node | Starts From | global@node | after_train | Δ_global |
|---|:---:|:---:|:---:|:---:|
| **Node 1** | W_agg_6 | **62.3%** | **67.1%** | **−14.9% ⚠** |
| Node 2 | W_agg_6 | 80.1% | 83.2% | +1.8% |
| Node 3 | W_agg_6 | 79.8% | 82.9% | +1.5% |

> **Interpreting the drop on Node 1**
>
> Node 1's `global@node` dropped from 77.2% (round 6) to 62.3% (round 7) — a **−14.9%** delta. The `!` marker in the accuracy report flags this. This means W_agg_6 generalises poorly to Node 1's local data distribution. Nodes 2 and 3 are unaffected; the issue is specific to Node 1's partition.
>
> **What happened:** the aggregation in round 6 likely shifted the global model toward Nodes 2 and 3's distribution at the expense of Node 1. This is the classic non-IID data imbalance effect in FedAvg.

All three nodes still publish their round 7 submodel policies. The aggregator collects all three (`minParams=3` satisfied), runs FedAvg, and produces W_agg_7. Round 7 then completes normally from the aggregator's perspective.

After round 7 completes on Node 1:
- `round_number["mnist"]` is now **8**
- `listen_for_start_round` is polling for `RoundStart(8)`
- `_rollback_pending["mnist"]` is `False`

**Accuracy report after round 7 (Node 1 only):**

```
============================================================
  index: mnist   node: node1
  global@node = accuracy of global model on this node's data (pre-train)
  delta_global = change vs previous round -- negative means rollback candidate
============================================================
  round  global@node  after_train  contributed   delta_global
  -----  -----------  -----------  -----------   ------------
      1        10.2%        52.4%       +42.2%            --
      2        57.3%        63.1%        +5.8%         +47.1
      3        65.4%        70.2%        +4.8%          +8.1
      4        70.1%        74.3%        +4.2%          +4.7
      5        74.4%        77.6%        +3.2%          +4.3
      6        77.2%        80.1%        +2.9%          +2.8
      7        62.3%        67.1%        +4.8%         -14.9  !
```

The `!` on round 7 and the large negative delta are your signal to check whether rollback is warranted. In this test we decide it is.

---

## 5. Triggering the Manual Rollback

### Decision

We want Node 1 to start round 8 from W_agg_6 — the last model where Node 1 had good accuracy — instead of W_agg_7.

> **Why round 6?**  
> `POST /rollback {"round": 6}` instructs the node to load W_agg_6. Internally `rollback_to_round` looks up `RoundStart(7)` on the blockchain (round + 1) because that policy's `initParams` *is* W_agg_6. It fetches and loads those weights.

### The curl Command

```bash
# Target Node 1 only. Nodes 2 and 3 are not rolled back.
curl -X POST http://localhost:8080/rollback \
     -H "Content-Type: application/json" \
     -d '{"round": 6, "reason": "round 7 accuracy dropped -14.9% on node1"}'
```

### Expected Response

```json
{
  "status": "success",
  "rolled_back_to_round": 6,
  "model_path": "/app/file_write/node1/mnist/7-agg_update.pkl",
  "message": "Model rolled back to round 6"
}
```

### What the Code Does Internally (Step by Step)

1. **`node_server.py:414`** — `_node_ready.clear()`. The listener thread for Node 1 blocks at `_node_ready.wait()` and will not start round 8 training until the rollback finishes.

2. **`rollback_manager.py:105`** — `find_roundstart_policy("mnist", 7, el_url)` queries the blockchain:
   ```
   blockchain get mnist where round_number = 7 and node_type = aggregator
   ```
   Returns the policy whose `initParams` = W_agg_6.

3. **`rollback_manager.py:129`** — `fetch_and_load_weights` downloads W_agg_6 using the same `copy_file_from_container` / `read_file` path as normal training. Deserialises with `pickle.load`, extracts `newUpdates`, calls `decode_params`, calls `data_handlers["mnist"].update_model(weights)`.

4. **`node.py:337–338`** — sets `_rollback_pending["mnist"] = True` and `_stale_round["mnist"] = 6`.

5. **`rollback_manager.py:178`** — writes a row to the `rollback_events` table:
   ```json
   {"node_name": "node1", "trigger_type": "manual", "from_round": 8, "to_round": 6, "status": "success"}
   ```

6. **`node_server.py:429`** — `_node_ready.set()`. Listener thread unblocks.

### Node 1 State After Rollback

| Field | Value |
|---|---|
| Active model weights | W_agg_6 (rolled back) |
| `round_number["mnist"]` | 8 (unchanged) |
| `_rollback_pending["mnist"]` | `True` |
| `_stale_round["mnist"]` | 6 |
| Listener polling for | `RoundStart(8)` |

---

## 6. Round 8: The Stale Round

> **⚠ Stale gradient warning**  
> Node 1 is about to contribute a gradient computed from W_agg_6, while Nodes 2 and 3 contribute gradients computed from W_agg_7. W_agg_8 will be a **mixed-provenance aggregate**. This is an accepted trade-off at this stage of implementation. The staleness does not crash the system and training continues.

### What Happens When RoundStart(8) Arrives on Node 1

The aggregator publishes `RoundStart(8)` with `initParams = W_agg_7`.

Node 1's listener thread, now unblocked, finds the policy at `node_server.py:205`. Before calling `train_model_params` it checks:

```python
skip_download = nodeInstance._rollback_pending.get("mnist", False)
# -> True
```

It logs the stale warning and clears the flag:

```
WARNING [mnist] Round 8: rollback active -- training from W_agg_6
        instead of W_agg_7. Stale gradient warning: aggregator will
        receive an update computed from an older global model.
```

`train_model_params` is called with `skip_download=True`. The `elif skip_download` branch executes — no download, no `update_model` call. The model already holds W_agg_6.

### Round 8 Per-Node Results

| Node | Starts From | Downloads? | global@node | after_train | Δ_global |
|---|:---:|:---:|:---:|:---:|:---:|
| **Node 1** *(stale)* | W_agg_6 | No | 77.1% | 80.0% | +14.8% |
| Node 2 | W_agg_7 | Yes | 82.4% | 84.6% | +2.3% |
| Node 3 | W_agg_7 | Yes | 82.1% | 84.2% | +2.3% |

**Node 1's `global@node` for round 8 is ≈77%** — the same level as round 6 — because the model it loaded *is* W_agg_6. This is your confirmation the rollback worked: the accuracy measurement reflects the rolled-back starting point.

### Aggregation of Round 8

All three nodes publish their round 8 submodel policies. The aggregator polls with `minParams=3` and collects all three:

```
W_agg_8 = FedAvg(θ1_from_W_agg_6, θ2_from_W_agg_7, θ3_from_W_agg_7)
```

The aggregator publishes `RoundStart(9)` with `initParams = W_agg_8`.

### After Round 8: Rollback State is Cleared

`_rollback_pending["mnist"]` was set to `False` before the training call. From round 9 onward Node 1 resumes normal behaviour and downloads `initParams` as every other node does.

---

## 7. Rounds 9–10: Recovery

| Round | Aggregator Action | Node 1 global | Node 1 train | Nodes 2&3 global (avg) | Nodes 2&3 train (avg) | Produces |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 8 *(stale)* | `RoundStart(8)`, `initParams=W_agg_7` | 77.1% | 80.0% | 82.3% | 84.4% | W_agg_8 (mixed) |
| 9 | `RoundStart(9)`, `initParams=W_agg_8` | 80.3% | 82.6% | 83.1% | 85.0% | W_agg_9 |
| 10 | `RoundStart(10)`, `initParams=W_agg_9` | 82.1% | 84.0% | 84.7% | 86.1% | W_agg_10 |

The mixed aggregation in round 8 produces W_agg_8 pulled slightly toward W_agg_6 on Node 1's component. Rounds 9 and 10 normalise as all three nodes resume training from the same global model.

---

## 8. Full Accuracy Report: Expected Output

Run this after all 10 rounds complete on any node:

```bash
curl http://localhost:8080/accuracy-report?index=mnist
```

#### Node 1

```
============================================================
  index: mnist   node: node1
  global@node = accuracy of global model on this node's data (pre-train)
  delta_global = change vs previous round -- negative means rollback candidate
============================================================
  round  global@node  after_train  contributed   delta_global
  -----  -----------  -----------  -----------   ------------
      1        10.2%        52.4%       +42.2%             --
      2        57.3%        63.1%        +5.8%          +47.1
      3        65.4%        70.2%        +4.8%           +8.1
      4        70.1%        74.3%        +4.2%           +4.7
      5        74.4%        77.6%        +3.2%           +4.3
      6        77.2%        80.1%        +2.9%           +2.8
      7        62.3%        67.1%        +4.8%          -14.9  !   <-- trigger
      8        77.1%        80.0%        +2.9%          +14.8      <-- stale round
      9        80.3%        82.6%        +2.3%           +3.2
     10        82.1%        84.0%        +1.9%           +1.8
```

#### Nodes 2 & 3 (unaffected by rollback)

```
============================================================
  index: mnist   node: node2
============================================================
  round  global@node  after_train  contributed   delta_global
  -----  -----------  -----------  -----------   ------------
      1        10.5%        55.1%       +44.6%             --
      2        58.6%        65.3%        +6.7%          +48.1
      3        66.1%        71.8%        +5.7%           +7.5
      4        71.4%        75.9%        +4.5%           +5.3
      5        75.2%        78.7%        +3.5%           +3.8
      6        78.3%        81.4%        +3.1%           +3.1
      7        80.1%        83.2%        +3.1%           +1.8
      8        82.4%        84.6%        +2.2%           +2.3   <-- normal, no stale
      9        83.1%        85.0%        +1.9%           +0.7
     10        84.7%        86.1%        +1.4%           +1.6
```

Notice that Nodes 2 and 3 have no interruption at round 8: their `delta_global` progresses normally.

---

## 9. Rollback History Endpoint

```bash
curl http://localhost:8080/rollback/history?index=mnist
```

```json
{
  "events": [
    {
      "node_name":    "node1",
      "index_name":   "mnist",
      "trigger_type": "manual",
      "from_round":   8,
      "to_round":     6,
      "reason":       "round 7 accuracy dropped -14.9% on node1",
      "status":       "success"
    }
  ]
}
```

`from_round = 8` because that was `round_number["mnist"]` at the time of the call — the round Node 1 was *about to* run when the rollback was triggered. `to_round = 6` is the target.

---

## 10. Test Verification Checklist

### Before the Rollback (Rounds 1–7)

- [ ] All 3 nodes log `Listening for start round R` for each round — confirms listener is alive.
- [ ] Aggregator logs `Step 4 Complete: model parameters aggregated` for rounds 1–7 — confirms FedAvg ran every round.
- [ ] `GET /accuracy-report?index=mnist` on Node 1 shows 7 rows after round 7 completes.
- [ ] Node 1 round 7 row has a large negative `delta_global` with `!` marker.
- [ ] Nodes 2 and 3 round 7 rows show no `!`.

### Triggering the Rollback

- [ ] `POST /rollback {"round": 6}` on port 8080 (Node 1) returns `"status": "success"`.
- [ ] Response contains `"rolled_back_to_round": 6`.
- [ ] `GET /rollback/history?index=mnist` on Node 1 shows one event with `from_round: 8, to_round: 6, status: "success"`.

### Round 8 — Confirming the Stale Training Path

- [ ] Node 1 log contains the stale warning line:
  ```
  WARNING [mnist] Round 8: rollback active -- training from W_agg_6
          instead of W_agg_7. Stale gradient warning ...
  ```
- [ ] Node 1 log **does not** contain a download log line for round 8 (no `copy_file_from_container` / `read_file` call between the stale warning and training-done message).
- [ ] Node 1 round 8 `global@node` is close to its round 6 value (≈77%), not its round 7 value (≈62%). Confirms the model was not overwritten by W_agg_7.
- [ ] Nodes 2 and 3 round 8 `global@node` continues to rise normally (no stale warning in their logs).
- [ ] Aggregator still produces W_agg_8 after round 8 (`minParams=3` satisfied, all three submodel policies present on the blockchain).

### Rounds 9–10 — Confirming Recovery

- [ ] Node 1 log for round 9 contains **no** stale warning — confirms `_rollback_pending` was cleared.
- [ ] All three nodes' `delta_global` values are positive in rounds 9 and 10.
- [ ] Node 1 round 9 `global@node` is above its round 8 value — confirms W_agg_8 incorporated the mixed-provenance update and continued improving.

---

## 11. Quick Reference: All Curl Commands

```bash
# -- Accuracy report (any node) --
curl http://localhost:8080/accuracy-report?index=mnist
curl http://localhost:8081/accuracy-report?index=mnist
curl http://localhost:8082/accuracy-report?index=mnist

# -- Trigger manual rollback on Node 1 --
curl -X POST http://localhost:8080/rollback \
     -H "Content-Type: application/json" \
     -d '{"round": 6, "reason": "round 7 accuracy dropped"}'

# -- Check rollback history --
curl http://localhost:8080/rollback/history?index=mnist

# -- Check current rollback config --
curl http://localhost:8080/rollback/config

# -- Update rollback config at runtime (no restart needed) --
curl -X PUT http://localhost:8080/rollback/config \
     -H "Content-Type: application/json" \
     -d '{"patience_rounds": 3, "min_delta": 2.0}'
```

---

## 12. Note on Decentralized FL

The round lifecycle described in this document applies to the centralized setup where one aggregator drives the `RoundStart` policies and all nodes pull from it.

In a decentralized setup, nodes can act as both trainers and aggregators. The rollback logic is **identical at the node level**: `_rollback_pending`, `skip_download`, `find_roundstart_policy`, and `fetch_and_load_weights` all function the same way regardless of who published the `RoundStart` policy. The difference is that in the decentralized case there is no single aggregator to coordinate a global rollback — each node rolls back independently, and the stale gradient concern is magnified if multiple nodes roll back simultaneously to different target rounds. Coordinated multi-node rollback is deferred to a future implementation pass.

> **Known limitation: stale gradient**  
> The current implementation intentionally introduces a stale gradient in round 8 when a rollback is active. Node 1's contribution to W_agg_8 is computed from W_agg_6, not W_agg_7. The aggregator applies equal weight to all contributions and has no knowledge of the staleness. The effect on convergence is not yet measured. A follow-up pass will add a staleness tag to the submodel policy so the aggregator can apply a staleness discount (FedASMU pattern).