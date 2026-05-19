"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/
"""
import json
import logging
import os
import pickle
import time
from dataclasses import dataclass
from typing import Optional

import requests

from platform_components.EdgeLake_functions.mongo_file_store import copy_file_from_container, read_file
from platform_components.EdgeLake_functions.blockchain_EL_functions import fetch_data_from_db

logger = logging.getLogger(__name__)


@dataclass
class RollbackConfig:
    enabled: bool = True
    auto_enabled: bool = False
    patience_rounds: int = 3
    min_delta: float = 0.0
    allow_manual: bool = True
    log_events: bool = True


def load_rollback_config() -> RollbackConfig:
    def _bool(key: str, default: bool) -> bool:
        return os.getenv(key, str(default)).lower() in ("true", "1", "yes")

    return RollbackConfig(
        enabled=_bool("ROLLBACK_ENABLED", True),
        auto_enabled=_bool("ROLLBACK_AUTO_ENABLED", False),
        patience_rounds=int(os.getenv("ROLLBACK_PATIENCE_ROUNDS", "3")),
        min_delta=float(os.getenv("ROLLBACK_MIN_DELTA", "0.0")),
        allow_manual=_bool("ROLLBACK_ALLOW_MANUAL", True),
        log_events=_bool("ROLLBACK_LOG_EVENTS", True),
    )


def get_accuracy_history(index: str, db_name: str, el_url: str, node_name: str) -> list:
    """
    Query node_accuracy for this node's own rounds on the given index, ordered by round_number.
    Filtered by node_name so auto-rollback decisions are based on local accuracy only,
    not a mix of all nodes on the same index.
    Uses run client () — the real distributed query path, same as /accuracy-report.
    Returns a list of row dicts: [{node_name, index_name, round_number, final_accuracy, ...}]
    """
    sql = (
        f"SELECT node_name, index_name, round_number, initial_accuracy, final_accuracy "
        f"FROM node_accuracy "
        f"WHERE index_name = '{index}' AND node_name = '{node_name}' "
        f"ORDER BY round_number"
    )
    tcp_addr = os.getenv("EXTERNAL_TCP_IP_PORT", "")
    try:
        payload = fetch_data_from_db(el_url, f'sql {db_name} format=json "{sql}"', tcp_addr)
        rows = payload.get("Query", []) if isinstance(payload, dict) else payload
        return rows if rows else []
    except Exception as e:
        logger.error(f"[{index}] get_accuracy_history failed: {e}")
        return []


def should_auto_rollback(history: list, config: RollbackConfig) -> bool:
    """
    Return True if accuracy has not improved by min_delta over the last patience_rounds.
    Requires at least patience_rounds + 1 entries before making any decision.
    """
    if not config.enabled or not config.auto_enabled:
        return False
    if len(history) <= config.patience_rounds:
        return False

    current = float(history[-1].get("initial_accuracy", 0))
    comparison = float(history[-1 - config.patience_rounds].get("initial_accuracy", 0))
    improvement = current - comparison
    return improvement < config.min_delta


def select_rollback_round(history: list, config: RollbackConfig) -> int:
    """
    Return the round number with the highest final_accuracy in the history.
    Excludes the current (last) round since that is the one being rolled back from.
    """
    if not history:
        raise ValueError("Cannot select rollback round from empty history")

    candidates = history[:-1] if len(history) > 1 else history
    best = max(candidates, key=lambda r: float(r.get("initial_accuracy", 0)))
    return int(best["round_number"])


def find_roundstart_policy(index: str, round_num: int, el_url: str) -> Optional[dict]:
    """
    Query the blockchain for the aggregator's RoundStart policy for round_num.
    Returns the inner policy dict {initParams, ip_port, rest_ip_port, ...} or None.
    This is the same query listen_for_start_round() uses to start each training round.
    """
    headers = {
        'User-Agent': 'AnyLog/1.23',
        'command': f'blockchain get {index} where round_number = {round_num} and node_type = aggregator',
    }
    try:
        response = requests.get(el_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"[{index}] find_roundstart_policy HTTP {response.status_code}")
            return None
        data = response.json()
        if not data:
            return None
        return data[0].get(index)
    except Exception as e:
        logger.error(f"[{index}] find_roundstart_policy failed: {e}")
        return None


def fetch_and_load_weights(node, index: str, policy: dict) -> str:
    """
    Pull the aggregator model weights for a given round and load them into the active model.
    Mirrors the fetch + deserialize + load path in Node.train_model_params().
    Returns the local file path of the downloaded weights file.
    """
    params_link = policy.get("initParams", "")
    ip_port = policy.get("ip_port", "")
    rest_ip_port = policy.get("rest_ip_port", "")

    if not params_link:
        raise ValueError("Policy has no initParams — cannot fetch weights")

    filename = params_link.split("/")[-1]
    local_path = f"{node.file_write_destination}/{index}/{filename}"

    if node.docker_running:
        response = copy_file_from_container(
            os.path.join(node.tmp_dir, index),
            node.docker_container_name,
            rest_ip_port,
            params_link,
            local_path,
            ip_port,
        )
    else:
        response = read_file(rest_ip_port, params_link, local_path, ip_port)

    if not response or response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch weights from {params_link}: "
            f"HTTP {getattr(response, 'status_code', 'no response')}"
        )

    time.sleep(1)  # let the file flush to disk, same as train_model_params()

    with open(local_path, "rb") as f:
        data = pickle.load(f)

    if not data or "newUpdates" not in data:
        raise ValueError(f"Downloaded weights file is missing 'newUpdates': {local_path}")

    weights = node.decode_params(data["newUpdates"])
    node.data_handlers[index].update_model(weights)
    logger.info(f"[{index}] Weights loaded from {local_path}")

    return local_path


def log_rollback_event(
    node,
    index: str,
    trigger_type: str,
    from_round: int,
    to_round: int,
    reason: str,
    status: str,
) -> None:
    """
    Write a rollback event to AnyLog table 'rollback_events'.
    Uses the same PUT/streaming pattern as push_accuracy().
    """
    row = {
        "node_name":    node.replica_name,
        "index_name":   index,
        "trigger_type": trigger_type,
        "from_round":   from_round,
        "to_round":     to_round,
        "reason":       reason,
        "status":       status,
    }
    headers = {
        "type":         "json",
        "dbms":         node.databases[index],
        "table":        "rollback_events",
        "mode":         "streaming",
        "Content-Type": "text/plain",
    }
    try:
        response = requests.put(url=node.edgelake_node_url, data=json.dumps(row), headers=headers)
        logger.info(
            f"[{index}] Rollback event logged: {trigger_type} "
            f"r{from_round}→r{to_round} status={status} HTTP={response.status_code}"
        )
    except Exception as e:
        logger.error(f"[{index}] Failed to log rollback event: {e}")