"""
time_server.py — NTP/Cristian's Algorithm Simulator


The Time Server acts as the authoritative clock source.
Clients connect to it, request the time, and use Cristian's Algorithm
to adjust their local clocks accounting for network round-trip delay.
"""

import socket
import threading
import time
import json
import logging
import random
import sys

# ─────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 5000
LOG_FORMAT = "%(asctime)s  [SERVER]  %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%H:%M:%S")
log = logging.getLogger("time_server")


class TimeServer:
    """
    Authoritative time server.

    Listens for client requests of the form:
        {"type": "time_request", "client_id": "<id>", "t0": <send_timestamp>}

    Responds with:
        {
            "type"       : "time_response",
            "server_time": <epoch_seconds>,   # T_server at moment of processing
            "t0"         : <original_t0>,     # echoed back so client can compute RTT
            "simulated_delay_ms": <ms>        # delay injected on server side
        }
    """

    def __init__(self, host: str = HOST, port: int = PORT,
                 sim_delay_min_ms: float = 20,
                 sim_delay_max_ms: float = 150):
        self.host = host
        self.port = port
        self.sim_delay_min = sim_delay_min_ms / 1000.0
        self.sim_delay_max = sim_delay_max_ms / 1000.0
        self._server_socket: socket.socket | None = None
        self._running = False
        self._clients_served = 0
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(10)
        log.info("Time Server started — listening on %s:%d", self.host, self.port)
        log.info("Simulated network delay: %d–%d ms",
                 int(self.sim_delay_min * 1000), int(self.sim_delay_max * 1000))

        try:
            while self._running:
                try:
                    self._server_socket.settimeout(1.0)
                    conn, addr = self._server_socket.accept()
                    t = threading.Thread(target=self._handle_client,
                                         args=(conn, addr), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            log.info("Server shutting down (KeyboardInterrupt).")
        finally:
            self.stop()

    def stop(self):
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._server_socket.close()
            self._server_socket = None
        log.info("Server stopped. Total clients served: %d", self._clients_served)

    # ── Internal ─────────────────────────────────────────────────────────
    def _handle_client(self, conn: socket.socket, addr):
        """Handle a single client connection in its own thread."""
        client_str = f"{addr[0]}:{addr[1]}"
        try:
            raw = conn.recv(4096).decode("utf-8")
            if not raw:
                return
            request = json.loads(raw)

            if request.get("type") != "time_request":
                log.warning("Unknown request type from %s: %s", client_str, request)
                return

            client_id = request.get("client_id", "unknown")
            t0 = request.get("t0", 0.0)

            # Inject simulated one-way network delay (server-side processing latency)
            delay = random.uniform(self.sim_delay_min, self.sim_delay_max)
            time.sleep(delay)

            server_time = time.time()           # T_server captured AFTER delay

            response = {
                "type"              : "time_response",
                "server_time"       : server_time,
                "t0"                : t0,
                "simulated_delay_ms": round(delay * 1000, 2),
            }
            conn.sendall(json.dumps(response).encode("utf-8"))

            with self._lock:
                self._clients_served += 1

            log.info("Served client %-10s | server_time=%.3f | injected_delay=%5.1f ms",
                     client_id, server_time, delay * 1000)

        except (json.JSONDecodeError, KeyError) as e:
            log.error("Bad request from %s: %s", client_str, e)
        except Exception as e:
            log.error("Error handling %s: %s", client_str, e)
        finally:
            conn.close()


# ─────────────────────────────────────────────
#  Entry-point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    srv = TimeServer(
        sim_delay_min_ms=20,
        sim_delay_max_ms=150,
    )
    srv.start()
