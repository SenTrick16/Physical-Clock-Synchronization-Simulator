# Group Number : 16
# Physical Clock Synchronization Simulator
### DS Mini Project 13 — Cristian's Algorithm / NTP

---

##  Short Architecture Description (3–5 lines)

A **Time Server** process listens on TCP port 5000 and acts as the authoritative NTP clock.  
Four **Client Node** processes each simulate a distributed node with an independent local clock that starts with a configurable offset and drifts at a fixed rate (ms/s).  
Each client executes **Cristian's Algorithm**: it records the send timestamp (T₀), receives the server's timestamp (T_server), measures the round-trip time (RTT = T₁ − T₀), and corrects its clock by "T_server + RTT/2 − T_local".  
Network latency is **simulated** (random 20–150 ms per request) to demonstrate the algorithm under realistic conditions.  
After synchronisation, nodes continue drifting — illustrating why **periodic re-synchronisation** (as in NTP) is essential.

---

##  How to Run

### Prerequisites

- Python 3.10+ (tested on 3.11 / 3.13)
- pip packages: matplotlib, numpy

### 1. Install Dependencies

```bash
pip install -r code/requirements.txt
```

### 2. Run the Full Simulation (recommended)

```bash
# Runs simulator + generates 4 plots in /code
python code/run_all.py
```

### 3. Run Only the Simulator (terminal output)

```bash
python code/simulator.py
# or with custom options:
python code/simulator.py --rounds 5 --drift-window 8
```

| Flag | Default | Description |
|------|---------|-------------|
| `--rounds` | `3` | Number of sync rounds per node |
| `--drift-window` | `5` | Seconds to observe drift re-appearance |

### 4. Generate Only Plots

```bash
python code/visualizer.py
# with --show to open interactive windows (requires display):
python code/visualizer.py --show
```

### 5. Run on Ubuntu / Linux (no changes needed)

```bash
# Identical commands — no OS-specific code
python3 code/simulator.py --rounds 3 --drift-window 5
python3 code/visualizer.py
```

---

##  File Structure

```
DS Project/
├── README.md            # This file (project root)
├── .gitignore           # Git ignore rules
├── group_details.txt    # Group member information
└── code/
    ├── time_server.py       # TCP time server — authoritative clock
    ├── client_node.py       # Distributed node with Cristian's Algorithm
    ├── simulator.py         # Orchestrator: runs nodes, prints results
    ├── visualizer.py        # Generates PNG charts
    ├── run_all.py           # One-command launcher (sim + plots)
    ├── requirements.txt     # Python dependencies
    ├── plot_architecture.png
    ├── plot_skew_comparison.png
    ├── plot_drift_reappearance.png
    └── plot_rtt.png
```

**Output PNGs** (generated in `/code`):
- `plot_skew_comparison.png`  — Clock skew before vs. after sync
- `plot_drift_reappearance.png` — Drift growing back over time
- `plot_rtt.png`              — Network RTT per round
- `plot_architecture.png`    — System architecture diagram

---

##  Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `matplotlib` | ≥ 3.7 | Charts & architecture diagram |
| `numpy` | ≥ 1.24 | Numerical arrays for plotting |
| `socket` | stdlib | TCP networking (built-in) |
| `threading` | stdlib | Concurrent client handling (built-in) |
| `json` | stdlib | Message serialisation (built-in) |

---

##  Algorithm — Cristian's Algorithm

```
Client                      Server
  |                            |
  |── time_request (T₀) ──────►|
  |                            |  (inject random delay: 20–150 ms)
  |◄── time_response ──────────|  { T_server, T₀ }
  |                            |
  T₁ = now()
  RTT = T₁ − T₀
  T_corrected = T_server + RTT/2
  offset = T_corrected − local_clock
  local_clock += offset        ← clock corrected!
```

**Key insight:** `RTT/2` estimates the one-way network delay, so the correction accounts for the time the response spent in transit.

---

##  Sample Output

```
════════════════════════════════════════════════════════════════════════
      Physical Clock Synchronization Simulator
      Cristian's Algorithm / NTP — DS Mini Project 13
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
  Node-A     @0s: +68 ms   @50%: +76 ms   @100%: +83 ms  ← drifting!
  Node-C     @0s: +43 ms   @50%: +55 ms   @100%: +68 ms  ← fastest drift
```

---

##  Group Details

  Members:
  1. Sonali Minj — Roll No: 241000076
  2. Sparrsh Sanghi — Roll No: 241000077
  3. Srishti Tripathi — Roll No: 241000078
  4. Sukhram Markam — Roll No: 241000079  
  5. Tanmay Kumar — Roll No: 241000080

---

##  What We Learned

1. **Cristian's Algorithm** corrects clock skew by accounting for half the RTT — a simple but effective heuristic.
2. **Clock drift** is inevitable; even after perfect synchronisation, clocks diverge again, which is why NTP re-syncs every 64–1024 seconds.
3. **Network asymmetry** (send vs. receive latency not being equal) limits Cristian's Algorithm accuracy — NTP's later versions use more sophisticated filtering.
4. **Concurrency**: real distributed systems run sync on multiple nodes simultaneously — simulated here with Python threads.
