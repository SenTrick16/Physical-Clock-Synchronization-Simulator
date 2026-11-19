"""
simulator.py — NTP/Cristian's Algorithm Simulator
Distributed Systems Mini Project — Project 13

Main simulation orchestrator.
Starts the time server in a background thread, creates 4 client nodes
with different initial offsets and drift rates, runs multiple synchronisation
rounds, and prints a rich terminal report with before/after comparisons and
drift re-appearance analysis.

Usage:
    python simulator.py              # defaults: 3 sync rounds, 5s drift window
    python simulator.py --rounds 5 --drift-window 8
"""

import argparse
import threading
import time
import sys
import os
from typing import List

# Local imports
from time_server import TimeServer
from client_node import ClientNode, SyncRecord, DriftRecord

# ─────────────────────────────────────────────
#  ANSI colour helpers (gracefully disabled on
#  systems / terminals that don't support them)
# ─────────────────────────────────────────────
USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR")

class C:
    RESET  = "\033[0m"   if USE_COLOR else ""
    BOLD   = "\033[1m"   if USE_COLOR else ""
    RED    = "\033[91m"  if USE_COLOR else ""
    GREEN  = "\033[92m"  if USE_COLOR else ""
    YELLOW = "\033[93m"  if USE_COLOR else ""
    CYAN   = "\033[96m"  if USE_COLOR else ""
    BLUE   = "\033[94m"  if USE_COLOR else ""
    MAGENTA= "\033[95m"  if USE_COLOR else ""
    WHITE  = "\033[97m"  if USE_COLOR else ""

def coloured_ms(ms: float, threshold_good=5.0, threshold_warn=20.0) -> str:
    """Format a millisecond value with colour based on magnitude."""
    s = f"{ms:+8.2f} ms"
    if abs(ms) <= threshold_good:
        return C.GREEN + s + C.RESET
    elif abs(ms) <= threshold_warn:
        return C.YELLOW + s + C.RESET
    else:
        return C.RED + s + C.RESET

def hr(char="─", width=72, color=C.CYAN):
    return color + char * width + C.RESET


# ─────────────────────────────────────────────
#  Simulation configuration
# ─────────────────────────────────────────────
# (client_id, initial_offset_seconds, drift_rate_ms_per_second)
NODE_CONFIGS = [
    ("Node-A", +2.500,  +3.0),   # 2.5 s ahead, drifts +3 ms/s
    ("Node-B", -1.800,  -1.5),   # 1.8 s behind, drifts -1.5 ms/s
    ("Node-C", +0.750,  +5.0),   # 0.75 s ahead, drifts +5 ms/s (fastest drift)
    ("Node-D", -3.200,  +0.8),   # 3.2 s behind, drifts slowly
]

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000


# ─────────────────────────────────────────────
#  Pretty-printing helpers
# ─────────────────────────────────────────────
def print_banner():
    print()
    print(hr("═"))
    print(C.BOLD + C.CYAN +
          "   Physical Clock Synchronization Simulator".center(72) + C.RESET)
    print(C.WHITE +
          "   Cristian's Algorithm / NTP — DS Mini Project 13".center(72) + C.RESET)
    print(hr("═"))
    print()


def print_initial_state(nodes: List[ClientNode]):
    print(hr())
    print(C.BOLD + "  INITIAL CLOCK STATE (before any synchronisation)" + C.RESET)
    print(hr())
    hdr = f"  {'Node':<10} {'Local Time':>14}  {'True Time':>14}  {'Skew':>12}"
    print(C.BOLD + hdr + C.RESET)
    print("  " + "─" * 68)
    for n in nodes:
        lt = n.local_time
        tt = n.true_time
        skew = n.skew_ms
        print(f"  {n.id:<10} {lt:>14.3f}  {tt:>14.3f}  {coloured_ms(skew)}")
    print()


def print_sync_round_header(round_num: int, total: int):
    print()
    print(hr("─"))
    print(C.BOLD + C.YELLOW +
          f"  SYNCHRONISATION ROUND {round_num} / {total}".center(72) + C.RESET)
    print(hr("─"))


def print_sync_results(records: List[SyncRecord]):
    if not records:
        print(C.RED + "  No sync records to display." + C.RESET)
        return
    hdr = (f"  {'Node':<10} {'Before (ms skew)':>18}  {'RTT':>8}"
           f"  {'1-way est.':>10}  {'Offset':>12}  {'After (ms skew)':>16}")
    print(C.BOLD + hdr + C.RESET)
    print("  " + "─" * 86)
    for r in records:
        before_skew = (r.local_before - r.server_time) * 1000  # crude
        after_skew_col = coloured_ms(r.offset_applied_ms, 5, 20)
        print(
            f"  {r.client_id:<10}"
            f"  {r.offset_applied_ms:>+12.2f} ms applied"
            f"  |  RTT={r.rtt_ms:>6.1f} ms"
            f"  |  1-way≈{r.estimated_one_way_ms:>5.1f} ms"
        )


def print_state_comparison(nodes: List[ClientNode], label: str):
    print()
    print(hr())
    print(C.BOLD + f"  CLOCK STATE — {label}" + C.RESET)
    print(hr())
    hdr = f"  {'Node':<10} {'Local Time':>14}  {'True Time':>14}  {'Skew':>12}"
    print(C.BOLD + hdr + C.RESET)
    print("  " + "─" * 68)
    for n in nodes:
        lt = n.local_time
        tt = n.true_time
        sk = n.skew_ms
        print(f"  {n.id:<10} {lt:>14.3f}  {tt:>14.3f}  {coloured_ms(sk)}")
    print()


def print_drift_analysis(nodes: List[ClientNode], drift_window: float):
    """
    Show how drift re-introduces skew after some time has elapsed
    without synchronisation.
    """
    print()
    print(hr("═"))
    print(C.BOLD + C.MAGENTA +
          f"  DRIFT RE-APPEARANCE ANALYSIS  (after {drift_window:.0f}s without sync)".center(72)
          + C.RESET)
    print(hr("═"))

    snapshot_before = {n.id: n.skew_ms for n in nodes}
    real_start = time.time()

    print(f"\n  Waiting {drift_window:.0f} seconds to let clocks drift …\n")

    # Sample drift at several intervals
    samples_per_node = {n.id: [] for n in nodes}
    checkpoints = [drift_window * f for f in (0.25, 0.5, 0.75, 1.0)]

    for cp in checkpoints:
        wait = cp - (time.time() - real_start)
        if wait > 0:
            time.sleep(wait)
        for n in nodes:
            samples_per_node[n.id].append((cp, n.skew_ms))

    print(C.BOLD + f"  {'Node':<10} {'@0s (after sync)':>18}  "
          f"{'@25%':>10}  {'@50%':>10}  {'@75%':>10}  {'@100%':>10}" + C.RESET)
    print("  " + "─" * 78)

    for n in nodes:
        pts = samples_per_node[n.id]
        vals = "  ".join(f"{v:>+8.2f}" for _, v in pts)
        before_s = f"{snapshot_before[n.id]:>+8.2f}"
        print(f"  {n.id:<10}  {before_s:>18}  {vals}")

    print()
    print(C.YELLOW + "  ► Drift rates cause skew to grow back over time," + C.RESET)
    print(C.YELLOW + "    illustrating why periodic re-synchronisation (like NTP) is essential." + C.RESET)
    print()


def print_summary_table(nodes: List[ClientNode]):
    print()
    print(hr("═"))
    print(C.BOLD + C.CYAN + "  FINAL SUMMARY — All Synchronisation Rounds".center(72) + C.RESET)
    print(hr("═"))

    for n in nodes:
        print()
        print(C.BOLD + f"  {n.id}  (drift rate: {n._drift_rate * 1000:+.2f} ms/s," +
              f"  initial offset: {n._initial_offset:+.3f} s)" + C.RESET)
        print(f"  {'Round':<6} {'Offset Applied':>16}  {'RTT':>8}  {'1-way est.':>12}  "
              f"{'Server Injected':>16}")
        print("  " + "─" * 62)
        for r in n.sync_history:
            print(f"  {r.round_num:<6} {r.offset_applied_ms:>+14.3f} ms"
                  f"  {r.rtt_ms:>6.1f} ms"
                  f"  {r.estimated_one_way_ms:>10.1f} ms"
                  f"  {r.injected_delay_ms:>14.1f} ms")

    print()
    print(hr("═"))
    print(C.GREEN + C.BOLD + "  Simulation complete." + C.RESET)
    print(hr("═"))
    print()


# ─────────────────────────────────────────────
#  Main simulation runner
# ─────────────────────────────────────────────
def run_simulation(rounds: int = 3, drift_window: float = 5.0):
    print_banner()

    # ── 1. Start server in background thread ───────────────────────────
    server = TimeServer(
        sim_delay_min_ms=20,
        sim_delay_max_ms=150,
    )
    srv_thread = threading.Thread(target=server.start, daemon=True)
    srv_thread.start()
    time.sleep(0.3)  # Give the server a moment to bind

    # ── 2. Create client nodes ─────────────────────────────────────────
    nodes: List[ClientNode] = []
    for cid, offset, drift in NODE_CONFIGS:
        nodes.append(ClientNode(
            client_id          = cid,
            initial_offset_s   = offset,
            drift_rate_ms_per_s= drift,
            server_host        = SERVER_HOST,
            server_port        = SERVER_PORT,
        ))

    # ── 3. Show initial state ──────────────────────────────────────────
    print_initial_state(nodes)

    # ── 4. Run sync rounds ─────────────────────────────────────────────
    for r in range(1, rounds + 1):
        print_sync_round_header(r, rounds)
        records = []
        sync_threads = []

        def do_sync(node, rnd, result_list):
            rec = node.synchronize(round_num=rnd)
            if rec:
                result_list.append(rec)

        for node in nodes:
            t = threading.Thread(target=do_sync, args=(node, r, records))
            sync_threads.append(t)
            t.start()

        for t in sync_threads:
            t.join()

        records.sort(key=lambda x: x.client_id)
        print_sync_results(records)
        print_state_comparison(nodes, f"After Round {r}")

        if r < rounds:
            gap = 1.5
            print(f"  (waiting {gap}s before next round to allow drift to show…)")
            time.sleep(gap)

    # ── 5. Drift re-appearance ─────────────────────────────────────────
    print_drift_analysis(nodes, drift_window)

    # ── 6. Summary table ──────────────────────────────────────────────
    print_summary_table(nodes)

    server.stop()


# ─────────────────────────────────────────────
#  CLI entry-point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Physical Clock Synchronization Simulator — Cristian's Algorithm"
    )
    parser.add_argument(
        "--rounds", type=int, default=3,
        help="Number of synchronisation rounds to run (default: 3)"
    )
    parser.add_argument(
        "--drift-window", type=float, default=5.0,
        help="Seconds to observe drift re-appearance after final sync (default: 5)"
    )
    args = parser.parse_args()

    run_simulation(rounds=args.rounds, drift_window=args.drift_window)
