"""
run_all.py — NTP/Cristian's Algorithm Simulator

Convenience script: runs the full simulation + generates all plots.
Equivalent to:
    python simulator.py --rounds 3 --drift-window 5
    python visualizer.py --rounds 3
"""

import subprocess
import sys
import os

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    py   = sys.executable

    print("=" * 60)
    print("  Step 1/2 — Running simulation …")
    print("=" * 60)
    subprocess.run([py, os.path.join(base, "simulator.py"),
                    "--rounds", "3", "--drift-window", "5"], check=True)

    print("=" * 60)
    print("  Step 2/2 — Generating visualisation plots …")
    print("=" * 60)
    subprocess.run([py, os.path.join(base, "visualizer.py"),
                    "--rounds", "3"], check=True)

    print("\n  ✓  Done! Check the /code folder for PNG plots.\n")

if __name__ == "__main__":
    main()
