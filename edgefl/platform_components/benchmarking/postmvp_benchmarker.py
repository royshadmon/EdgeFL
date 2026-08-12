import threading
import queue
import logging
import time
import requests

logger = logging.getLogger(__name__)

class Benchmarker:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.state = {} # json pseudo policy with benchmarks
        self.session = requests.Session()

        # DAEMON Queue thread, run in the background asynchronously
        self.worker = threading.Thread(target=self._run_worker, daemon=True)

        self.worker.start()

    def record_node_round_start(self, training_index, node_name, round_number):
        now = time.time()
        key = (training_index, node_name)

        with self.lock:
            node_state = self.state.setdefault(key, {})
            wait_time_s = None
            if "last_round_end_ts" in node_state:
                wait_time_s = now - node_state["last_round_end_ts"]
            node_state["round_start_ts"] = now

        self.q.put({
            "event": "node_round_start",
            "training_index": training_index,
            "node_name": node_name,
            "round_number": round_number,
            "ts": now,
            "wait_time_s": wait_time_s,
        })


    def record_node_round_end(self, training_index, node_name, round_number):
        now = time.time()
        key = (training_index, node_name)

        with self.lock:
            node_state = self.state.setdefault(key, {})
            start_ts = node_state.get("round_start_ts")
            training_time_s = (now - start_ts) if start_ts is not None else None
            node_state["last_round_end_ts"] = now

        # Push to queue
        self.q.put({
            "event": "node_round_end",
            "training_index": training_index,
            "node_name": node_name,
            "round_number": round_number,
            "ts": now,
            "wait_time_s": training_time_s, 
        })


    def record_accuracy(self, training_index, node_name, round_number, accuracy):
        self.q.put({
            "event": "accuracy",
            "training_index": training_index,
            "node_name": node_name,
            "round_number": round_number,
            "accuracy": accuracy,
            "ts": time.time(),
        })


    def record_agg_metrics(self, training_index, round_number, **metrics):
        self.q.put({
            "event": "agg_metrics",
            "training_index": training_index,
            "round_number": round_number,
            "ts": time.time(),
            **metrics,
        })

    def _run_worker(self):
        while True:
            record = self.q.get()
            try:
                response = self.session.post(self.endpoint, json=record, timeout=5)
                if response.status_code >= 400:
                    logger.warning(
                        "Bnechmarker POST failed: %s %s", response.status_code, response.text
                    )
            except requests.exceptions.RequestException as e:
                logger.error("Benchmarker POST error: %s", str(e))
            except Exception as e:
                logger.error("Benchmarker unexpected error: %s", str(e))
            finally:
                self.q.task_done()



