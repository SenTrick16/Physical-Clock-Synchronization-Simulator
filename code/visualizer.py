"""
visualizer.py — NTP/Cristian's Algorithm Simulator
Distributed Systems Mini Project — Project 13

Generates charts showing:
  1. Clock skew before vs after synchronisation for each node
  2. Drift re-appearance over time (skew growing back after each sync)
  3. RTT measurements per round per node
  4. Architecture diagram (text-art + matplotlib figure)

Usage:
    python visualizer.py          # runs mini simulation + plots (saves PNGs)
    python visualizer.py --show   # also opens interactive windows
"""

import argparse
import threading
import time
import os
import sys
import matplotlib
matplotlib.use("Agg")           # non-interactive backend (safe on headless Linux)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from time_server import TimeServer
from client_node import ClientNode

# ─────────────────────────────────────────────
#  Node configs (must match simulator.py)
# ─────────────────────────────────────────────
NODE_CONFIGS = [
    ("Node-A", +2.500,  +3.0),
    ("Node-B", -1.800,  -1.5),
    ("Node-C", +0.750,  +5.0),
    ("Node-D", -3.200,  +0.8),
]
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001            # different port so it can run alongside simulator.py
OUTPUT_DIR  = os.path.dirname(os.path.abspath(__file__))

COLORS = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]


# ─────────────────────────────────────────────
#  Run a quick simulation for data collection
# ─────────────────────────────────────────────
def collect_data(rounds: int = 3, drift_window: float = 6.0):
    server = TimeServer(
        host="0.0.0.0", port=SERVER_PORT,
        sim_delay_min_ms=20, sim_delay_max_ms=150,
    )
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    time.sleep(0.3)

    nodes = [
        ClientNode(cid, offset, drift, SERVER_HOST, SERVER_PORT)
        for cid, offset, drift in NODE_CONFIGS
    ]

    # Initial skew
    initial_skews = {n.id: n.skew_ms for n in nodes}

    # --- Sync rounds + drift snapshots ---
    skew_after_round   = {n.id: [] for n in nodes}  # skew right after each sync
    rtt_per_round      = {n.id: [] for n in nodes}
    skew_post_drift    = {n.id: [] for n in nodes}  # skew sampled over drift window

    for r in range(1, rounds + 1):
        sync_threads = []
        for node in nodes:
            st = threading.Thread(target=node.synchronize, args=(r,))
            sync_threads.append(st)
            st.start()
        for st in sync_threads:
            st.join()

        for n in nodes:
            skew_after_round[n.id].append(n.skew_ms)
            if n.sync_history:
                rtt_per_round[n.id].append(n.sync_history[-1].rtt_ms)
            else:
                rtt_per_round[n.id].append(0)

        # Sample drift between rounds
        t0 = time.time()
        checkpoints = np.linspace(0, drift_window / rounds, 8)
        for cp in checkpoints:
            w = cp - (time.time() - t0)
            if w > 0:
                time.sleep(w)
            for n in nodes:
                skew_post_drift[n.id].append((r * drift_window / rounds + cp, n.skew_ms))

    server.stop()
    return nodes, initial_skews, skew_after_round, rtt_per_round, skew_post_drift, rounds, drift_window


# ─────────────────────────────────────────────
#  Plot 1 — Skew Before vs After
# ─────────────────────────────────────────────
def plot_skew_comparison(nodes, initial_skews, skew_after_round, rounds, save=True):
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(nodes))
    w = 0.35

    before_vals = [initial_skews[n.id] for n in nodes]
    # Use average skew across all rounds after sync
    after_vals  = [np.mean(skew_after_round[n.id]) for n in nodes]

    bars_b = ax.bar(x - w/2, before_vals, w, label="Before Sync", color="#C44E52", alpha=0.85)
    bars_a = ax.bar(x + w/2, after_vals,  w, label="After Sync",  color="#55A868", alpha=0.85)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels([n.id for n in nodes], fontsize=11)
    ax.set_ylabel("Clock Skew (ms)", fontsize=11)
    ax.set_xlabel("Node", fontsize=11)
    ax.set_title("Clock Skew — Before vs After Cristian's Algorithm Synchronisation",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Annotate bars
    for bar in bars_b:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + (50 if h >= 0 else -150),
                f"{h:+.0f}", ha="center", va="bottom", fontsize=8, color="#C44E52")
    for bar in bars_a:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + (50 if h >= 0 else -150),
                f"{h:+.1f}", ha="center", va="bottom", fontsize=8, color="#2a7a4f")

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "plot_skew_comparison.png")
    if save:
        fig.savefig(path, dpi=150)
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────
#  Plot 2 — Drift Re-appearance Over Time
# ─────────────────────────────────────────────
def plot_drift_reappearance(nodes, skew_post_drift, save=True):
    fig, ax = plt.subplots(figsize=(10, 5))

    for idx, n in enumerate(nodes):
        pts = skew_post_drift[n.id]
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.8,
                label=n.id, color=COLORS[idx % len(COLORS)])

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_xlabel("Elapsed Time (s)", fontsize=11)
    ax.set_ylabel("Clock Skew vs True Time (ms)", fontsize=11)
    ax.set_title("Drift Re-appearance Over Time (skew returns without periodic sync)",
                 fontsize=12, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(linestyle="--", alpha=0.4)

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "plot_drift_reappearance.png")
    if save:
        fig.savefig(path, dpi=150)
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────
#  Plot 3 — RTT per Round
# ─────────────────────────────────────────────
def plot_rtt(nodes, rtt_per_round, rounds, save=True):
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(1, rounds + 1)

    for idx, n in enumerate(nodes):
        rtts = rtt_per_round[n.id]
        ax.plot(x[:len(rtts)], rtts[:rounds], marker="s", linewidth=1.8,
                label=n.id, color=COLORS[idx % len(COLORS)])

    ax.set_xlabel("Sync Round", fontsize=11)
    ax.set_ylabel("Round-Trip Time (ms)", fontsize=11)
    ax.set_title("Network RTT per Synchronisation Round (simulated)", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.legend(fontsize=10)
    ax.grid(linestyle="--", alpha=0.4)

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "plot_rtt.png")
    if save:
        fig.savefig(path, dpi=150)
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────
#  Plot 4 — Architecture Diagram
# ─────────────────────────────────────────────
def plot_architecture(save=True):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def draw_box(x, y, w, h, label, sublabel="", color="#4C72B0", fontsize=10):
        rect = mpatches.FancyBboxPatch((x, y), w, h,
                                       boxstyle="round,pad=0.15",
                                       linewidth=1.5, edgecolor=color,
                                       facecolor=color + "30")
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2 + (0.15 if sublabel else 0),
                label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=color)
        if sublabel:
            ax.text(x + w/2, y + h/2 - 0.3, sublabel,
                    ha="center", va="center", fontsize=7.5, color="#444")

    def arrow(x1, y1, x2, y2, label="", color="gray"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="<->", color=color, lw=1.4))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx + 0.1, my, label, fontsize=7.5, color=color,
                    ha="left", va="center")

    # Time Server
    draw_box(3.8, 5.0, 2.4, 1.1, "Time Server", "Authoritative Clock\n(NTP Server)", "#1565C0", 10)

    # Clients
    positions = [(0.3, 2.5), (2.8, 2.5), (5.3, 2.5), (7.8, 2.5)]
    labels    = ["Node-A\n+2.5s, +3ms/s", "Node-B\n-1.8s, -1.5ms/s",
                 "Node-C\n+0.75s, +5ms/s", "Node-D\n-3.2s, +0.8ms/s"]

    for (cx, cy), lbl in zip(positions, labels):
        draw_box(cx, cy, 1.9, 1.1, lbl.split("\n")[0],
                 lbl.split("\n")[1], "#2E7D32", 9)
        arrow(cx + 0.95, cy + 1.1, 5.0, 5.0, "", "#888")

    # Labels
    ax.text(5.0, 4.75, "① T0: Request sent (local clock)", fontsize=7.5, color="#555")
    ax.text(5.0, 4.45, "② Server responds with T_server", fontsize=7.5, color="#555")
    ax.text(5.0, 4.15, "③ RTT = T1 − T0", fontsize=7.5, color="#555")
    ax.text(5.0, 3.85, "④ T_corrected = T_server + RTT/2", fontsize=7.5, color="#C44E52", fontweight="bold")

    # Drift arrow
    ax.annotate("", xy=(9.3, 2.0), xytext=(0.3, 2.0),
                arrowprops=dict(arrowstyle="->", color="#999", lw=1.2, linestyle="dashed"))
    ax.text(4.8, 1.75, "Clock drift causes skew to grow back ➜ periodic re-sync needed",
            ha="center", fontsize=8, color="#888", style="italic")

    ax.set_title("Architecture: Physical Clock Synchronization (Cristian's Algorithm)",
                 fontsize=12, fontweight="bold", pad=10)

    fig.tight_layout()
    path = os.path.join(OUTPUT_DIR, "plot_architecture.png")
    if save:
        fig.savefig(path, dpi=150)
        print(f"  Saved → {path}")
    return fig


# ─────────────────────────────────────────────
#  Entry-point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate visualisation plots")
    parser.add_argument("--show",   action="store_true", help="Show interactive plot windows")
    parser.add_argument("--rounds", type=int, default=3, help="Sync rounds for data collection")
    args = parser.parse_args()

    print("\n  Collecting simulation data …")
    nodes, initial_skews, skew_after_round, rtt_per_round, skew_post_drift, rounds, dw = \
        collect_data(rounds=args.rounds)

    print("\n  Generating plots …")
    figs = [
        plot_skew_comparison(nodes, initial_skews, skew_after_round, rounds),
        plot_drift_reappearance(nodes, skew_post_drift),
        plot_rtt(nodes, rtt_per_round, rounds),
        plot_architecture(),
    ]

    if args.show:
        matplotlib.use("TkAgg")
        for f in figs:
            f.show()
        plt.show(block=True)

    print("\n  All plots saved. ✓\n")
