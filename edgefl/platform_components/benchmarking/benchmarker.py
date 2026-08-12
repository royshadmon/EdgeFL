import threading
import queue
import logging
import time
import json
import requests


logger = logging.getLogger(__name__)

class Benchmarker:
    def __init__(self, endpoint:str, db_name:str = "benchmarkfl", table_name: str = "fl_benchmarks", enabled: bool = True):
        self.enabled = enabled
        if not enabled:
            logger.info("Benchmarker disabled (BENCHMARK is set to False). No metrics will be recorded.")
            return
        
        self.endpoint = endpoint
        self.session = requests.Session()

        # Refuse any target that can't ingest streaming data, i.e. master nodes 
        if not self._verify_target_availability():
            self.enabled = False
            logger.warning(
                "Benchmark target %s has no Operator process running and can't ingest data."
                "DISABLING BENCHMARKING, point BENCHMARK_REST_CONN at an operator node.", 
                self.endpoint,
            )
            return

        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.state = {} # json pseudo policy with benchmark

        self.metrics = [
                "training_time_s", 
                "polling_time_s", 
                "total_round_time_s", 
                "first_to_last_arrival_s",
                "straggling_node_id",
                "round_accuracy",
                "aggregation_time_s"
            ]

        # table header
        self.header = {
                "type": "json",
                "dbms": db_name,
                "table": table_name,
                "mode": "streaming",
                "Content-Type": "text/plain",
                "User-Agent": "AnyLog/1.23",
        }

        self._ensure_dbms_connected()
        logger.info(f"Benchmarker initialized: \n  endpoint = {self.endpoint}\n  dbms = {db_name}\n  table = {table_name}")
        # DAEMON Queue thread, run in the background asynchronously
        self.worker = threading.Thread(target=self._run_worker, daemon=True)
        self.worker.start()

    def _get_connected_dbms(self):
        hearders = {
                "User-Agent": "Anylog/1.23",
                "command": "get databases",
        }
        resp = self.session.get(self.endpoint, headers=hearders, timeout=5)
        resp.raise_for_status()

        lines = resp.text.strip().split("\r\n")
        data_lines = lines[3:]
        dbms = set()
        for line in data_lines:
            parts = [part.strip() for part in line.split("|")]
            if parts and parts[-1] == "":
                parts = parts[:-1]
            if len(parts) == 6:
                dbms.add(parts[0])
        return dbms

    def _connect_sqlite_dbms(self, db_name):
        headers = {
                "User-Agent": "Anylog/1.23",
                "command": f"connect dbms {db_name} where type = sqlite and memory = false",
        }

        resp = self.session.post(self.endpoint, headers=headers, timeout=5)
        resp.raise_for_status()

    def _ensure_dbms_connected(self):
        try:
            connected = self._get_connected_dbms()
            if self.header["dbms"] not in connected:
                logger.info("Benchmark dbms missing; connecting %s", self.header["dbms"])
                self._connect_sqlite_dbms(self.header["dbms"])
        except Exception as e:
            logger.warning("Benchmarker dbms connection failed: %s", str(e))

    def _verify_target_availability(self) -> bool:
        """
        This methor probes the endpoint to check whether it's possible to ingest data
        True if only the endpoint's node has an Operator process running.  
        """
        try: 
            r = self.session.get(
                    self.endpoint,
                    headers = {"User-Agent": "Anylog/1.23", "command": "get processes"},
                    timeout = 5,
                )
            r.raise_for_status()
        except Exception as e:
            logger.warning("Benchmarker could not probe target %s: %s", self.endpoint, str(e))
            return False
        
        for line in r.text.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if parts and parts[0].lower() == "operator":
                status = parts[1].lower() if len(parts) > 1 else ""
                return status.startswith("running")
        return False


    def record_simple_metric(self, 
                             training_index, 
                             round_number, 
                             node_name, 
                             metric_name, 
                             metric_value, 
                             timestamp=None):

        if not self.enabled:
            return

        if metric_name not in self.metrics:
            logger.warning(f"Benchmarker called with incorrect metric_name value: {metric_name}")
            return


        payload = {
            "node": node_name,
            "training_index": training_index, 
            "round_number": round_number,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "time": time.time() if timestamp is None else timestamp, 
        }

        self.q.put(payload)


    def _run_worker(self):
        while True:
            record = self.q.get()
            try:
                response = self.session.put(
                        self.endpoint, 
                        data=json.dumps(record), 
                        headers=self.header, 
                        timeout=5,
                )

                if response.status_code >= 400:
                    logger.warning(
                        "Bnechmarker POST failed: %s %s", response.status_code, response.text
                    )

            except requests.exceptions.RequestException as e:
                logger.error("Benchmarker PUT error: %s", str(e))
            except Exception as e:
                logger.error("Benchmarker unexpected error: %s", str(e))
            finally:
                self.q.task_done()

