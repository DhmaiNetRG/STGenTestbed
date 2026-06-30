#!/usr/bin/env python3
"""
STGen vs Gotham/GothX memory footprint as a function of emulated node count.

STGen points are the measured process-based resource-scaling data
(results/scalability_results.json): one OS process per node, memory as summed PSS.

Gotham/GothX run emulated IoT devices as Docker containers and network
infrastructure (routers) as QEMU VMs. GothX (poisson2024gothx) derived Gotham's
memory footprint as R = 37*d + 470*q MB, where d is the number of Docker device
nodes and q the number of QEMU router VMs; their 450-device run (498 Docker + 4
QEMU) used 498*37 + 4*470 = 20.3 GB, matching the reported 20.4 GB. Each emulated
IoT device therefore costs ~37 MB. We plot that 37 MB/node Docker cost; the 16 GB
workstation RAM is drawn as a reference ceiling.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, NullFormatter

# ---------------------------------------------------------------- data
rows = json.load(open("results/scalability_results.json"))
stg_n = np.array([r["Nodes"] for r in rows], float)
stg_m = np.array([r["PSS (GB)"] * 1000.0 for r in rows], float)   # process-tree PSS, MB

got_n = np.array([1, 25, 50, 100, 200, 300, 450], float)
got_m = 37.0 * got_n                                              # 37 MB per Docker IoT node

RAM_MB = 16 * 1024                                                # 16 GB host
Y_TOP = 60000
X_LO, X_HI = 0.8, 9000

# ---------------------------------------------------------------- style
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 10,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
})
C_GOTHAM = "#C44E00"   # muted vermillion
C_STGEN  = "#0B5394"   # deep blue
C_LIMIT  = "#555555"
C_DROP   = "#888888"

fig, ax = plt.subplots(figsize=(6.6, 4.4))

# infeasible region above the host RAM (solid light fill so EPS renders cleanly)
ax.axhspan(RAM_MB, Y_TOP, facecolor="#f4f4f4", edgecolor="none", zorder=0)
ax.axhline(RAM_MB, color=C_LIMIT, ls=(0, (6, 4)), lw=1.0, zorder=1)
ax.text(X_HI / 1.04, RAM_MB * 1.16, "16 GB host RAM",
        fontsize=8.5, color=C_LIMIT, ha="right", va="bottom", zorder=5)

# vertical drop-lines marking the node count at each curve's reference point
for x, y, lab, col in [(443, RAM_MB, "440", C_GOTHAM), (6000, 622, "6000", C_STGEN)]:
    ax.plot([x, x], [30, y], ls=":", lw=0.9, color=C_DROP, zorder=1)
    ax.scatter([x], [y], s=26, color=col, zorder=4, edgecolor="white", linewidth=0.7)
    ax.annotate(lab, xy=(x, 30), xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=8.2, color=col, zorder=5)

# curves: hollow markers, thin connecting lines
ax.plot(got_n, got_m, marker="s", ls="--", color=C_GOTHAM, ms=5.2, lw=1.6,
        mfc="white", mew=1.3, clip_on=False, zorder=3,
        label="Gotham/GothX (Docker container, 37 MB/node)")
ax.plot(stg_n, stg_m, marker="o", ls="-", color=C_STGEN, ms=5.2, lw=1.6,
        mfc="white", mew=1.3, clip_on=False, zorder=3,
        label="STGen (OS process, 99 KB/node)")

# ---------------------------------------------------------------- axes
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(X_LO, X_HI)
ax.set_ylim(30, Y_TOP)
ax.set_xlabel("Number of emulated nodes")
ax.set_ylabel("Memory footprint (MB)")

ax.xaxis.set_major_locator(LogLocator(base=10))
ax.yaxis.set_major_locator(LogLocator(base=10))
ax.xaxis.set_minor_formatter(NullFormatter())
ax.yaxis.set_minor_formatter(NullFormatter())
ax.grid(True, which="major", ls="-", lw=0.5, color="#cccccc", zorder=0)
ax.grid(True, which="minor", ls=":", lw=0.4, color="#e6e6e6", zorder=0)
ax.set_axisbelow(True)

leg = ax.legend(loc="upper left", fontsize=8.6, frameon=True, framealpha=0.96,
                edgecolor="#cccccc", borderpad=0.6, handlelength=2.4)
leg.get_frame().set_linewidth(0.8)

fig.tight_layout()
for ext in ("eps", "png"):
    fig.savefig(f"images/stgenVsGotham.{ext}", dpi=600, bbox_inches="tight")
plt.close(fig)

print("wrote images/stgenVsGotham.eps and .png")
print(f"STGen:  {stg_m[0]:.0f}->{stg_m[-1]:.0f} MB over {stg_n[0]:.0f}->{stg_n[-1]:.0f} nodes")
print(f"Gotham: 16 GB at n={RAM_MB/37:.0f} Docker IoT nodes; per-node ratio 37 MB / 99 KB = {37*1024/99:.0f}x")
