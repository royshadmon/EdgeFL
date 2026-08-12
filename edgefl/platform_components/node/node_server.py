"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""
import traceback
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse

# from dotenv import load_dotenv
from platform_components.EdgeLake_functions.blockchain_EL_functions import get_local_ip, \
    connect_to_db, get_all_databases, get_policies, fetch_data_from_db
from platform_components.node.node import Node
# import numpy as np
import logging
import threading
import time
from dotenv import load_dotenv
import os
import argparse
import requests
import warnings

from uvicorn import run
from fastapi import FastAPI, HTTPException, status

from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional

from platform_components.node.rollback_manager import (
    RollbackConfig, load_rollback_config,
    get_accuracy_history, should_auto_rollback, select_rollback_round,
)

from platform_components.lib.logger.logger_config import configure_logging

from platform_components.benchmarking.benchmarker import Benchmarker

warnings.filterwarnings("ignore")

load_dotenv()

edgelake_node_url = f'http://{os.getenv("EXTERNAL_IP")}'
edgelake_node_port = edgelake_node_url.split(":")[2]

configure_logging(f"node_server_{edgelake_node_port}")

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)  # Excludes WARNING, ERROR, CRITICAL

# BENCH - Initialize Benchmarking
_bench_conn = os.getenv("BENCHMARK_REST_CONN") or os.getenv("EXTERNAL_IP")
if not _bench_conn:
    raise RuntimeError("Neither BENCHMARK_REST_CONN nor EXTERNAL_IP is set; cannot init Benchmarker.")

_bench_endpoint = _bench_conn if _bench_conn.startswith("http") else f"http://{_bench_conn}"

_bench_enabled = os.getenv("BENCHMARK_ENABLED", "true").strip().lower() not in ("false", "0", "no", "off")
bench = Benchmarker(_bench_endpoint, enabled=_bench_enabled)

# Initialize the Node instance
node_instance = None
listener_thread = None
stop_listening_thread = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # logger.info("Node server shutting down.")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



rollback_cfg: RollbackConfig = load_rollback_config()

# Guards the listener thread during rollback so aggregator weights can't
# overwrite the rolled-back model before it gets a chance to be used.
_node_ready = threading.Event()
_node_ready.set()  # starts in "ready" state; cleared only during rollback


class InitNodeRequest(BaseModel):
    replica_name: str
    replica_ip: str
    replica_port: str
    replica_index: str
    round_number: int


class RollbackRequest(BaseModel):
    round: int
    reason: Optional[str] = "manual"


class RollbackConfigUpdate(BaseModel):
    auto_enabled: Optional[bool] = None
    patience_rounds: Optional[int] = None
    min_delta: Optional[float] = None
    allow_manual: Optional[bool] = None
    log_events: Optional[bool] = None


# When the aggregator calls this endpoint, three things happen:
# 1) A node object is created
# 2) The node loads. its training app (MnistDataHandler) dynamically from the env config
# 3) A daemon thread is spwaned that immediately starts polling the blockchaing
#  POST /init-node  →  Node()  →  listen_for_start_round() thread starts
# TODO: look into how daemon threads work
@app.post('/init-node')
def init_node(request: InitNodeRequest):
    global node_instance, listener_thread, stop_listening_thread
    try:
        ip = get_local_ip()
        most_recent_round = request.round_number

        port = request.replica_port
        replica_name = request.replica_name
        index = request.replica_index

        module_name = os.getenv("MODULE_NAME")
        module_file = os.getenv("MODULE_FILE")

        db_name = os.getenv("LOGICAL_DATABASE")

        # Instantiate the Node class
        # Where nodes are made
        # Held under node_isntance 
        # each node instance has: (replica name, ip, port, logger)
        logger.info(f"{replica_name} before initialized")
        if not node_instance:
            node_instance = Node(replica_name, ip, port, logger)

        if index not in node_instance.databases:
            node_instance.databases[index] = db_name

        node_instance.initialize_specific_node_on_index(index, module_name, module_file)
        node_instance.round_number[index] = most_recent_round # 1 or current round

        logger.info(f"{replica_name} successfully initialized for ({index})")
        # print(f"indexes: {node_instance.indexes}")
        # print(f"module names: {node_instance.module_names}")
        # print(f"module paths: {node_instance.module_paths}")
        # print(f"starting round numbers: {node_instance.round_number}")
        # print(f"training apps: {node_instance.data_handlers}")

        # Start event listener for start round
        listener_thread = threading.Thread(
            name=f"{replica_name}--{index}",
            target=listen_for_start_round,
            args=(node_instance, index, lambda: stop_listening_thread)
        )
        listener_thread.daemon = True  # Make thread daemon so it exits when main thread exits
        listener_thread.start()

        return {
            'status': 'success',
            'message': 'Node initialized successfully'
        }
    except ValueError as e:
        raise ValueError(
            f"No data found in the database: {os.getenv('LOGICAL_DATABASE')}"   #changed temp for 3.11 "" -> ''
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"/init-node - {str(e)}"
        )
    except ConnectionError as e:
        raise ConnectionError(
            f"Unable to access the database tables: {str(e)}"
        )

# This loop runs forever on its own thread. Every 5 seconds it asks the blockchain
# Has the aggregator published a RoundStart policy for round N?

def listen_for_start_round(nodeInstance, index, stop_event):
    current_round = nodeInstance.round_number[index]

    logger.info(f"[{index}][Round {current_round}] Listening for start round {current_round}")

    # benchmarking: mark beginning of polling time for this round
    listen_start_ts = time.time()

    while True:
        try:
            headers = {
                'User-Agent': 'AnyLog/1.23',
                'command': f'blockchain get {index} where round_number = {current_round} and node_type = aggregator'
                # This command line, when it finds one, it extracts initParams (the path to the aggregated model file) and calls train_model_params()
                # train_model_params() called here!
            }
            response = requests.get(edgelake_node_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                # if no policies, then wait 2 seconds
                if not data:
                    time.sleep(2)
                    continue
                round_data = data[0].get(index)
                # for item in data:
                #     # Check if the key exists in the current dictionary
                #     if f'{index}-r{current_round}' in item:
                #         round_data = item.get(index).get("initParams")
                #         break  # Stop searching once the current round's data is found

                if round_data:
                    # rollback: block while a rollback is in progress so its weights
                    # aren't overwritten the moment the next round fires, then resync.
                    _node_ready.wait()
                    current_round = nodeInstance.round_number[index]

                    logger.debug(f"[{index}] Round Data: {round_data}")

                    # rollback: if a rollback is pending, skip downloading initParams this
                    # round and train directly from the rolled-back weights already in the model.
                    # WARNING: this node's update will be stale relative to the current global
                    # model — W_agg_{current_round-1} — and may pull aggregation in an older
                    # direction. Use staleness-aware aggregation if this is a concern.
                    skip_download = nodeInstance._rollback_pending.get(index, False)
                    if skip_download:
                        nodeInstance._rollback_pending[index] = False
                        logger.warning(
                            f"[{index}] Round {current_round}: rollback active — "
                            f"training from W_agg_{nodeInstance._stale_round.get(index, '?')} "
                            f"instead of W_agg_{current_round - 1}. "
                            f"Stale gradient warning: aggregator will receive an update "
                            f"computed from an older global model."
                        )

                    # benchmarking: mark beginning of training time
                    round_start_ts = time.time()

                    paramsLink = round_data.get('initParams', '')
                    ip_port = round_data.get('ip_port', '')
                    rest_ip_port = round_data.get('rest_ip_port', '')

                    result = nodeInstance.train_model_params(paramsLink, current_round, ip_port, rest_ip_port, index, skip_download=skip_download)

                    # Reminder: add_node_params() writes a submodel blockchain policy so the aggregator can find this node's model file.
                    nodeInstance.add_node_params(current_round, result['model_path'], index)    #Goes to blockchain

                    # benchmarking: mark end of training time
                    round_end_ts = time.time()

                    logger.info(f"[{index}][Round {current_round}] Step 3 Complete: Model parameters published")

                    # benchmarking: timing metrics
                    training_time_s = round_end_ts - round_start_ts
                    polling_time_s = round_start_ts - listen_start_ts
                    total_round_time_s = round_end_ts - listen_start_ts
                    logger.info(
                            f"Benchmarker [{index}][Round {current_round}] "
                            f" * training time={training_time_s:.3f}s"
                            f" * polling time={polling_time_s:.3f}s"
                            f" * total round time={total_round_time_s:.3f}s"
                    )
                    bench.record_simple_metric(index, current_round, nodeInstance.replica_name, "training_time_s", training_time_s)
                    bench.record_simple_metric(index, current_round, nodeInstance.replica_name, "polling_time_s", polling_time_s)
                    bench.record_simple_metric(index, current_round, nodeInstance.replica_name, "total_round_time_s", total_round_time_s)

                    # forward post-training accuracy into benchmarkfl 
                    bench.record_simple_metric(index, current_round, nodeInstance.replica_name, "round_accuracy", result['final_accuracy'])

                    # accuracy: distributed node_accuracy store consumed by rollback
                    nodeInstance.push_accuracy(index, current_round, result['initial_accuracy'], result['final_accuracy'], result['model_path'])
                    current_round += 1
                    nodeInstance.round_number[index] = current_round
                    logger.info(f"[{index}][Round {current_round}] Listening for start round {current_round}")

                    # benchmarking: reset polling clock for next round
                    listen_start_ts = time.time()

                    # rollback: auto-rollback runs only when ROLLBACK_AUTO_ENABLED=true
                    if rollback_cfg.auto_enabled:
                        db_name = os.getenv("LOGICAL_DATABASE", "mnist_fl")
                        history = get_accuracy_history(index, db_name, edgelake_node_url, nodeInstance.replica_name)
                        if should_auto_rollback(history, rollback_cfg):
                            target = select_rollback_round(history, rollback_cfg)
                            logger.info(f"[{index}] Auto-rollback triggered: target round={target}")
                            try:
                                nodeInstance.rollback_to_round(index, target, reason="automatic", trigger_type="automatic")
                                logger.info(f"[{index}] Auto-rollback complete, resuming from round {current_round}")
                            except Exception as rollback_err:
                                logger.error(f"[{index}] Auto-rollback failed: {rollback_err}")

            time.sleep(5)  # Poll every 2 seconds
        except Exception as e:
            logger.error(f"[{index}] Error in listener thread: {str(e)}")
            time.sleep(2)

# TODO: move to a (helper) file (i.e. 'node_helpers.py'?)
# Extracts initParams from the policy 'index-r' at the specified index
def get_most_recent_agg_params(index):
    policy_name = f"{index}-r"
    agg_params = None

    try:
        headers = {
            'User-Agent': 'AnyLog/1.23',
            'command': f'blockchain get {index}'
        }
        response = requests.get(edgelake_node_url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            if data:
                policy = data[0]
                policy_data = policy[policy_name]
                agg_params = policy_data["initParams"]

        return agg_params
    except Exception as e:
        logger.error(f"[{index}] Error in extracting round number: {str(e)}")

# @app.route('/inference', methods=['POST'])
@app.post('/inference/{index}', response_class=PlainTextResponse)
def inference(index):
    """Inference on current model w/ data passed in."""
    try:
        logger.info(f"[{index}] received inference request")
        if not index:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Index must be specified."
            )
        results = node_instance.inference(index)
        response = {
                    'index': f'{index}',
                    'status': 'success',
                    'message': 'Inference completed successfully',
                    'model_accuracy': f'{str(results)}'
                    }
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

class InferenceRequest(BaseModel):
    input: list
    index: str

# TODO: add index and reformat response to FastAPI PlainTextResponse
# @app.route('/infer', methods=['POST'])
@app.post('/infer')
def direct_inference(request: InferenceRequest):
    """Inference on current model w/ data passed in."""
    try:
        float_list = request.input
        index = request.index
        results = node_instance.direct_inference(index, float_list)
        response = {
            'prediction': str(results),
        }
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error executing inference on model. Check inference function in data handler"
        )

# REMOVED: _current_accuracy_table() computed a partition table name like
#   par_node_accuracy_2026_05_01_d14_insert_timestamp
# and the /accuracy-report endpoint below queried it directly with a bare `sql` command.
# Both are wrong per AnyLog's intended query interface:
#   1. Partition tables are for debug inspection only — logical table is the correct target.
#   2. `sql ...` queries only the local node; `run client () sql ...` queries the full network.
# Keeping the old implementation commented out below as a fallback reference.
#
# def _current_accuracy_table() -> str:
#     from datetime import datetime, timezone
#     now = datetime.now(timezone.utc)
#     period_start = (now.day // 14) * 14
#     return f"par_node_accuracy_{now.year}_{now.month:02d}_{period_start:02d}_d14_insert_timestamp"


@app.get('/accuracy-report', response_class=PlainTextResponse)
def accuracy_report(index: str = None):
    """
    Query node_accuracy from AnyLog and print one table per index_name.

    Usage:
        curl http://localhost:8080/accuracy-report
        curl "http://localhost:8080/accuracy-report?index=NodeAccTest11"
    """
    try:
        db_name = os.getenv("LOGICAL_DATABASE", "mnist_fl")
        where_clause = f"WHERE index_name = '{index}'" if index else ""
        sql = (
            f"SELECT node_name, index_name, round_number, initial_accuracy, final_accuracy "
            f"FROM node_accuracy {where_clause} ORDER BY index_name, round_number"
        )
        query = f'sql {db_name} format=json "{sql}"'

        operators = get_policies(edgelake_node_url, index='operator')
        rows = []
        for op in operators:
            rest_url = f"http://{op['ip']}:{op['rest_port']}"
            tcp_addr = f"{op['ip']}:{op['port']}"
            try:
                payload = fetch_data_from_db(rest_url, query, tcp_addr)
                rows.extend(payload.get("Query", []) if isinstance(payload, dict) else [])
            except Exception:
                pass

        if not rows:
            # Previously: f"No accuracy data found in {table}.\n" — `table` was the old partition table variable, now removed.
            return f"No accuracy data found in node_accuracy.\n"

        # Group by (index_name, node_name) so each node gets its own table
        groups: dict[tuple, list] = {}
        for row in rows:
            key = (row.get('index_name', 'unknown'), row.get('node_name', 'unknown'))
            groups.setdefault(key, []).append(row)

        lines = []
        # Column headers:
        #   round        — training round number
        #   global@node  — initial_accuracy: how well W_agg_{R-1} performs on THIS node's
        #                  local test set before any training (measures global model quality
        #                  from this node's perspective)
        #   after_train  — final_accuracy: accuracy after this node's local fine-tuning
        #   contributed  — improvement this node added (after_train - global@node)
        #   Δ_global     — change in global@node vs previous round (is the global model
        #                  improving for this node? negative = rollback candidate)
        header = f"  {'round':>5}  {'global@node':>11}  {'after_train':>11}  {'contributed':>11}  {'Δ_global':>8}"
        sep    = f"  {'-----':>5}  {'-----------':>11}  {'-----------':>11}  {'-----------':>11}  {'--------':>8}"
        for (idx_name, node_name) in sorted(groups):
            idx_rows = groups[(idx_name, node_name)]
            lines.append(f"\n{'=' * 60}")
            lines.append(f"  index: {idx_name}   node: {node_name}")
            lines.append(
                f"  global@node = accuracy of global model on this node's data (pre-train)\n"
                f"  Δ_global    = change vs previous round — negative means rollback candidate"
            )
            lines.append(f"{'=' * 60}")
            lines.append(header)
            lines.append(sep)
            prev_initial = None
            for row in idx_rows:
                init_acc  = float(row['initial_accuracy'])
                final_acc = float(row['final_accuracy'])
                contributed = final_acc - init_acc
                if prev_initial is None:
                    delta_str = f"{'--':>8}"
                else:
                    delta = init_acc - prev_initial
                    sign = "+" if delta >= 0 else ""
                    marker = "  !" if delta < -5 else ""
                    delta_str = f"{sign}{delta:>7.1f}{marker}"
                prev_initial = init_acc
                lines.append(
                    f"  {row['round_number']:>5}  "
                    f"{init_acc:>10.1f}%  "
                    f"{final_acc:>10.1f}%  "
                    f"{'+' if contributed >= 0 else ''}{contributed:>10.1f}%  "
                    f"{delta_str}"
                )
        return "\n".join(lines) + "\n"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/rollback')
def rollback(request: RollbackRequest):
    """
    Manual rollback to a specific round.
    Fetches the aggregator-published model weights for that round via the blockchain
    RoundStart policy and loads them as the active model.
    """
    if not rollback_cfg.enabled:
        raise HTTPException(status_code=403, detail="Rollback is disabled on this node")
    if not rollback_cfg.allow_manual:
        raise HTTPException(status_code=403, detail="Manual rollback is disabled on this node")
    if not node_instance:
        raise HTTPException(status_code=400, detail="Node is not initialized")

    index = next(iter(node_instance.indexes), None)
    if not index:
        raise HTTPException(status_code=400, detail="No index initialized on this node")

    _node_ready.clear()  # pause the listener thread before touching model weights
    try:
        result = node_instance.rollback_to_round(
            index, request.round,
            reason=request.reason or "manual",
            trigger_type="manual",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _node_ready.set()  # always resume, even on error


@app.get('/rollback/config')
def get_rollback_config():
    """Return the current rollback configuration (env defaults + any runtime overrides)."""
    return {
        "rollback_enabled":  rollback_cfg.enabled,
        "auto_enabled":      rollback_cfg.auto_enabled,
        "patience_rounds":   rollback_cfg.patience_rounds,
        "min_delta":         rollback_cfg.min_delta,
        "allow_manual":      rollback_cfg.allow_manual,
        "log_events":        rollback_cfg.log_events,
    }


@app.put('/rollback/config')
def update_rollback_config(request: RollbackConfigUpdate):
    """Update rollback config at runtime (in-memory only, does not persist to .env)."""
    global rollback_cfg
    if request.auto_enabled is not None:
        rollback_cfg.auto_enabled = request.auto_enabled
    if request.patience_rounds is not None:
        rollback_cfg.patience_rounds = request.patience_rounds
    if request.min_delta is not None:
        rollback_cfg.min_delta = request.min_delta
    if request.allow_manual is not None:
        rollback_cfg.allow_manual = request.allow_manual
    if request.log_events is not None:
        rollback_cfg.log_events = request.log_events

    return {"status": "success", "config": {
        "rollback_enabled":  rollback_cfg.enabled,
        "auto_enabled":      rollback_cfg.auto_enabled,
        "patience_rounds":   rollback_cfg.patience_rounds,
        "min_delta":         rollback_cfg.min_delta,
        "allow_manual":      rollback_cfg.allow_manual,
        "log_events":        rollback_cfg.log_events,
    }}


@app.get('/rollback/history')
def rollback_history(index: str = None):
    """
    Query rollback_events from AnyLog via run client () — the distributed network path.
    Optional ?index= filter to scope by training index.
    """
    try:
        db_name = os.getenv("LOGICAL_DATABASE", "mnist_fl")
        where_clause = f"WHERE index_name = '{index}'" if index else ""
        sql = (
            f"SELECT node_name, index_name, trigger_type, from_round, to_round, reason, status "
            f"FROM rollback_events {where_clause} ORDER BY index_name, from_round"
        )
        tcp_addr = os.getenv("EXTERNAL_TCP_IP_PORT", "")
        try:
            payload = fetch_data_from_db(edgelake_node_url, f'sql {db_name} format=json "{sql}"', tcp_addr)
        except Exception:
            return {"events": []}
        rows = payload.get("Query", []) if isinstance(payload, dict) else payload
        return {"events": rows if rows else []}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    global port
    parser = argparse.ArgumentParser(description="Run the Node Server.")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on.")
    args = parser.parse_args()

    run(
    "node_server:app",
        host="0.0.0.0",
        port=args.port,
        reload=False  # Enable auto-reload on code changes (optional)
    )
