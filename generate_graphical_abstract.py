#!/usr/bin/env python3
"""
Graphical abstract for the STGen paper (MDPI JSAN).

Frames the existing architecture diagram (images/base-diagram.png, with its
ELK/MongoDB logos and device icons) with a title strip and a key-results ribbon,
so the abstract conveys both the system and its headline outcomes.

Output: images/graphical_abstract.{png,pdf}
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
})

# Muted slate-navy echoing the diagram's cloud-outline ink (academic, restrained)
TITLE_BG  = "#34495E"
RIBBON_BG = "#2C3E50"
SUBTEXT   = "#C3CDD8"
DIVIDER   = "#55697C"

diagram = mpimg.imread("images/base-diagram.png")
dh, dw = diagram.shape[0], diagram.shape[1]
ratio = dw / dh  # ~1.966

# Layout fractions (title / diagram / results ribbon)
F_TITLE, F_IMG, F_STATS = 0.115, 0.75, 0.135
FIG_W = 13.0
img_h_in = FIG_W / ratio                 # keep the diagram undistorted
FIG_H = img_h_in / F_IMG

fig = plt.figure(figsize=(FIG_W, FIG_H))

# --- title strip ---
ax_t = fig.add_axes([0, F_STATS + F_IMG, 1, F_TITLE]); ax_t.axis("off")
ax_t.add_patch(plt.Rectangle((0, 0), 1, 1, color=TITLE_BG, zorder=0))
ax_t.text(0.5, 0.54,
          "STGen: a lightweight, physically-grounded testbed for scenario-based IoT protocol evaluation",
          ha="center", va="center", color="white", fontsize=15, weight="bold")

# --- architecture diagram (unchanged) ---
ax_i = fig.add_axes([0, F_STATS, 1, F_IMG]); ax_i.axis("off")
ax_i.imshow(diagram, aspect="auto", interpolation="lanczos")

# --- key-results ribbon ---
ax_s = fig.add_axes([0, 0, 1, F_STATS]); ax_s.axis("off")
ax_s.add_patch(plt.Rectangle((0, 0), 1, 1, color=RIBBON_BG, zorder=0))
stats = [
    ("6,000 nodes", "@ 99 KB/node, 1.02 s"),
    ("Fidelity", "KS $D=0.071$ vs 1.83M readings"),
    ("Protocol", "MQTT/CoAP live↔emulated inversion"),
    ("Anomalies", "labelled, 7×6, AUC 1.0 / 0.90"),
]
n = len(stats)
for i, (big, small) in enumerate(stats):
    x = (i + 0.5) / n
    ax_s.text(x, 0.62, big, ha="center", va="center", color="white",
              fontsize=12.5, weight="bold")
    ax_s.text(x, 0.30, small, ha="center", va="center", color=SUBTEXT,
              fontsize=10.5)
    if i:  # divider
        ax_s.plot([i / n, i / n], [0.18, 0.82], color=DIVIDER, lw=1.0)

fig.savefig("images/graphical_abstract.png", dpi=300, facecolor="white", bbox_inches="tight")
fig.savefig("images/graphical_abstract.pdf", facecolor="white", bbox_inches="tight")
plt.close(fig)
print(f"wrote images/graphical_abstract.png and .pdf  (canvas ratio w/h = {FIG_W/FIG_H:.2f})")
