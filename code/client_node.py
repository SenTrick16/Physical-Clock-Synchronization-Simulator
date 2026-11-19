"""
client_node.py — NTP/Cristian's Algorithm Simulator
Distributed Systems Mini Project — Project 13

Each ClientNode represents a distributed node with:
  • Its own local clock (offset from real time + drift rate)
  • Logic to request time from the server
  • Cristian's Algorithm to compute the correction

Cristian's Algorithm:
    T_corrected = T_server + (RTT / 2)
    offset      = T_corrected − T_local_at_response
"""

import socket
import threading
import time
import json
import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional

LOG_FORMAT = "%(asctime)s  [%(name)-12s]  %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%H:%M:%S")


# ─────────────────────────────────────────────
#  Data Containers
# ─────────────────────────────────────────────
@dataclass
class SyncRecord:
    """Stores the result of a single synchronisation attempt."""
    client_id       : str
    round_num       : int
    local_before    : float   # local clock just before sync
    server_time     : float   # T_server from server
    rtt_ms          : float   # measured round-trip time in ms
    estimated_one_way_ms: float
    offset_applied_ms: float  # correction applied (ms)
    local_after     : float   # local clock after correction
    injected_delay_ms: float  # delay the server admits to injecting


@dataclass
class DriftRecord:
    """Tracks drift between sync rounds."""
    client_id  : str
    elapsed_s  : float
    drift_ms   : float        # accumulated drift since last sync


# ─────────────────────────────────────────────
#  ClientNode
# ─────────────────────────────────────────────
class ClientNode:
    """
    Simulated distributed node.

    Parameters
    ----------
    client_id       : human-readable label, e.g. "Node-1"
    initial_offset_s: initial clock skew relative to real time (seconds)
    drift_rate_ms_per_s: how many ms the clock drifts per second of real time
    server_host     : hostname / IP of the time server
    server_port     : port of the time server
    """

    def __init__(self,
                 client_id: str,
                 initial_offset_s: float,
                 drift_rate_ms_per_s: float,
                 server_host: str = "127.0.0.1",
                 server_port: int = 5000):
        self.id = client_id
        self._initial_offset = initial_offset_s          # fixed skew at start
        self._drift_rate = drift_rate_ms_per_s / 1000.0  # converted to s/s
        self._correction = 0.0                            # Cristian correction (s)
        self._start_real = time.time()                    # reference real-time

        self.server_host = server_host
        self.server_port = server_port

        self.sync_history  : List[SyncRecord]  = []
        self.drift_history : List[DriftRecord] = []
        self._last_sync_local: Optional[float] = None
        self._lock = threading.Lock()
        self._log = logging.getLogger(client_id)

    # ── Clock API ────────────────────────────────────────────────────────
    @property
    def local_time(self) -> float:
        """
        Returns the node's local clock reading (simulated).
        local_time = real_time + initial_offset + drift_accumulated + correction
        """
        real_now    = time.time()
        elapsed     = real_now - self._start_real
        drift_accum = elapsed * self._drift_rate
        with self._lock:
            correction = self._correction
        return real_now + self._initial_offset + drift_accum + correction

    @property
    def true_time(self) -> float:
        """Real system time (ground truth for comparison)."""
        return time.time()

    @property
    def skew_ms(self) -> float:
        """Current skew between this node's clock and true time (ms)."""
        return (self.local_time - self.true_time) * 1000.0

    # ── Cristian's Algorithm ─────────────────────────────────────────────
    def synchronize(self, round_num: int = 1) -> Optional[SyncRecord]:
        """
        Perform one Cristian's Algorithm synchronisation round.

        1. Record T0 = local clock when request is sent
        2. Send request to time server
        3. Receive T_server in response
        4. Record T1 = local clock when response arrives
        5. RTT  = T1 − T0
        6. T_corrected = T_server + RTT/2          (Cristian's formula)
        7. offset = T_corrected − T1               (how much we need to shift)
        8. Apply offset to local correction
        """
        local_before = self.local_time
        t0_real      = time.time()     # real send time

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5.0)
                sock.connect((self.server_host, self.server_port))

                request = json.dumps({
                    "type"     : "time_request",
                    "client_id": self.id,
                    "t0"       : t0_real,
                })
                sock.sendall(request.encode("utf-8"))
                raw = sock.recv(4096).decode("utf-8")

            t1_real  = time.time()       # real receive time
            response = json.loads(raw)

            rtt      = t1_real - t0_real                  # total RTT (real seconds)
            T_server = response["server_time"]
            injected = response.get("simulated_delay_ms", 0.0)

            # ── Cristian's core formula ──────────────────────────────────
            T_corrected   = T_server + (rtt / 2.0)
            local_at_t1   = self.local_time               # read local clock NOW
            offset        = T_corrected - local_at_t1     # +ve ⟹ local is behind

            with self._lock:
                self._correction += offset

            local_after = self.local_time

            rec = SyncRecord(
                client_id            = self.id,
                round_num            = round_num,
                local_before         = local_before,
                server_time          = T_server,
                rtt_ms               = rtt * 1000,
                estimated_one_way_ms = (rtt / 2.0) * 1000,
                offset_applied_ms    = offset * 1000,
                local_after          = local_after,
                injected_delay_ms    = injected,
            )
            self.sync_history.append(rec)
            self._last_sync_local = local_after

            self._log.info(
                "Round %d | RTT=%6.1f ms | offset=%+7.2f ms | skew_after=%+7.2f ms",
                round_num, rtt * 1000, offset * 1000, self.skew_ms
            )
            return rec

        except socket.timeout:
            self._log.error("Round %d — connection timed out!", round_num)
        except ConnectionRefusedError:
            self._log.error("Round %d — server refused connection. Is server running?", round_num)
        except Exception as e:
            self._log.error("Round %d — unexpected error: %s", round_num, e)
        return None

    def record_drift(self, elapsed_s: float):
        """Record current drift for display/analysis."""
        dr = DriftRecord(
            client_id = self.id,
            elapsed_s = elapsed_s,
            drift_ms  = self.skew_ms,
        )
        self.drift_history.append(dr)
        return dr
