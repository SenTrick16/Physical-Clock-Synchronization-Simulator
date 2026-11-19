# Physical Clock Synchronization Simulator
### Cristian's Algorithm & NTP — Python Implementation

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## Overview

A from-scratch Python simulation of **distributed clock synchronization** using **Cristian's Algorithm** — the foundational protocol behind NTP (Network Time Protocol).

The project models a realistic distributed system: a central **Time Server** and four **Client Nodes**, each with an independent local clock that starts with a configurable offset and drifts over time. Nodes synchronize by estimating one-way network latency (`RTT / 2`) and correcting their clocks accordingly — the same core mechanism used in production NTP deployments.

### Why this is interesting
- Demonstrates a real distributed systems problem: **clock skew and drift** across nodes with no shared memory
- Uses **TCP sockets + threads** to simulate a live network environment
- Visualizes synchronization effectiveness with **4 annotated charts** (matplotlib)
- Fully configurable via CLI flags — easy to experiment with

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Time Server                          │
│         TCP :5000  ·  authoritative clock               │
│         Injects simulated latency: 20–150 ms            │
└────────────────────────┬────────────────────────────────┘
                         │  TCP (Cristian's Algorithm)
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   [Node-A]         [Node-B]         [Node-C/D]
  +2.5 s offset    -1.8 s offset     ±drift rates
  +3 ms/s drift    -1.5 ms/s         configurable
```

**Cristian's Algorithm:**
```
Client                      Server
  |── time_request (T₀) ──────►|
  |◄── time_response ──────────|  { T_server, T₀ }
  T₁ = now()
  RTT = T₁ − T₀
  T_corrected = T_server + RTT/2    ← accounts for transit time
  offset = T_corrected − local_clock
  local_clock += offset             ← clock corrected
```

---

## Features

| Feature | Detail |
|---|---|
| **Cristian's Algorithm** | Full implementation with RTT/2 compensation |
| **Simulated network latency** | Random 20–150 ms per request (configurable) |
| **Clock drift** | Per-node drift rates (ms/s) that persist after sync |
| **Concurrent sync** | All nodes synchronize in parallel using Python threads |
| **Drift re-appearance** | Post-sync drift window shows why periodic sync matters |
| **Rich terminal output** | ANSI-coloured, tabular reports with before/after skew |
| **4 visualisation charts** | Skew comparison, drift over time, RTT, architecture diagram |

---

## Getting Started

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/SenTrick16/DS-Project.git
cd DS-Project
pip install -r code/requirements.txt
```

### Run the Full Simulation (recommended)

```bash
python code/run_all.py
```

This runs the simulator **and** generates all 4 plots in the `code/` folder.

### Run Only the Simulator

```bash
python code/simulator.py

# With custom options:
python code/simulator.py --rounds 5 --drift-window 8
```

| Flag | Default | Description |
|------|---------|-------------|
| `--rounds` | `3` | Number of sync rounds per node |
| `--drift-window` | `5` | Seconds to observe drift re-appearance |

### Generate Only Plots

```bash
python code/visualizer.py

# Open interactive windows (requires display):
python code/visualizer.py --show
```

---

## Output

**Terminal** — colour-coded round-by-round sync report:

```
════════════════════════════════════════════════════════════════════════
      Physical Clock Synchronization Simulator
════════════════════════════════════════════════════════════════════════

INITIAL CLOCK STATE (before any synchronisation)
  Node       Local Time        True Time         Skew
  Node-A     ...               ...          +2500.00 ms
  Node-B     ...               ...          -1800.00 ms
  Node-C     ...               ...           +750.00 ms
  Node-D     ...               ...          -3200.00 ms

SYNCHRONISATION ROUND 1 / 3
  Node-A   -2477.67 ms applied | RTT= 46.2 ms | 1-way≈ 23.1 ms
  ...

DRIFT RE-APPEARANCE ANALYSIS (after 5s without sync)
  Node-A   @0s: +68 ms   @50%: +76 ms   @100%: +83 ms  ← drifting!
```

**Generated PNGs** (saved to `code/`):

| File | Shows |
|------|-------|
| `plot_skew_comparison.png` | Clock skew before vs. after each sync round |
| `plot_drift_reappearance.png` | Drift growing back over time post-sync |
| `plot_rtt.png` | Network RTT measured per round per node |
| `plot_architecture.png` | System architecture diagram |

---

## Project Structure

```
DS-Project/
├── README.md
├── .gitignore
└── code/
    ├── time_server.py       # TCP time server — authoritative clock source
    ├── client_node.py       # Distributed node with Cristian's Algorithm
    ├── simulator.py         # Orchestrator: runs nodes, prints coloured report
    ├── visualizer.py        # Generates 4 matplotlib charts
    ├── run_all.py           # One-command launcher (simulation + plots)
    ├── requirements.txt     # Python dependencies
    ├── plot_architecture.png
    ├── plot_skew_comparison.png
    ├── plot_drift_reappearance.png
    └── plot_rtt.png
```

---

<<<<<<< HEAD
## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `matplotlib` | ≥ 3.7 | Charts & architecture diagram |
| `numpy` | ≥ 1.24 | Numerical arrays for plotting |
| `socket` | stdlib | TCP networking |
| `threading` | stdlib | Concurrent client sync |
| `json` | stdlib | Message serialisation |

---

## Key Takeaways
=======
##  What We Learned
>>>>>>> 892084fe76cf906f8df4cbdde0230b536b1d17d3

1. **RTT/2 compensation** is a simple but effective heuristic — accurate when send/receive latencies are symmetric.
2. **Clock drift is inevitable** — even after a perfect sync, clocks diverge again, which is why NTP re-syncs every 64–1024 seconds.
3. **Network asymmetry** limits Cristian's Algorithm accuracy — NTP's later versions (NTPv4) use more sophisticated filtering and multiple server references.
4. **Thread-based concurrency** realistically models simultaneous sync across multiple nodes.

---

## License

MIT — free to use, fork, and build on.
