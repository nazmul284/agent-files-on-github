"""Figures from results/summary.json. usage: uv run --with matplotlib python charts.py <out_dir>"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

s = json.loads((Path(__file__).resolve().parent.parent / "results" / "summary.json").read_text())
out = Path(sys.argv[1])
INK, MUTED, GRID = "#1f2328", "#6b7280", "#eeeeee"
COL = {"AGENTS.md": "#0f766e", "Claude Code (CLAUDE.md)": "#c2410c", "Copilot": "#2563eb",
       "Cursor (.cursor/rules)": "#7c3aed", "Gemini CLI": "#64748b"}
LAB = {"AGENTS.md": "AGENTS.md (Codex and 20+ others)", "Claude Code (CLAUDE.md)": "CLAUDE.md (Claude Code)",
       "Copilot": "copilot-instructions.md", "Cursor (.cursor/rules)": ".cursor/rules (Cursor)", "Gemini CLI": "GEMINI.md"}
FOOT = ("Random sample of 1,200 GitHub repos with 1,000+ stars pushed in the 30 days to 6 Oct 2026 · "
        "first commit of each file still present today · github.com/nazmul284/agent-files-on-github")

# 1. adoption curves, established cohort
months = s["months"]; i0 = months.index("2025-01")
fig, ax = plt.subplots(figsize=(10, 5.6), dpi=200)
x = range(len(months) - i0)
for k, c in COL.items():
    y = s["adoption_established"][k][i0:]
    ax.plot(x, y, color=c, lw=2.4 if k in ("AGENTS.md", "Claude Code (CLAUDE.md)") else 1.8)
    nudge = {"Gemini CLI": -0.45, "Cursor (.cursor/rules)": 0.45}.get(k, 0)   # these two end 0.5 points apart
    ax.text(len(x) - 0.6, y[-1] + nudge, f" {LAB[k]} {y[-1]:.1f}%", color=c, fontsize=9.5, va="center")
ticks = [i for i, m in enumerate(months[i0:]) if m.endswith(("-01", "-07"))]
ax.set_xticks(ticks, [months[i0 + i][:7].replace("-01", " Jan").replace("-07", " Jul") for i in ticks])
ax.set_ylim(0, 22); ax.set_xlim(0, len(x) + 10)
ax.set_ylabel("% of repos with the file", fontsize=10, color=MUTED)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
ax.tick_params(colors=MUTED); ax.grid(axis="y", color=GRID)
fig.text(0.02, 0.96, "Level for nine months, then AGENTS.md pulled away in July 2026", fontsize=14, weight="bold", color=INK)
fig.text(0.02, 0.915, "Share of popular, active GitHub repos carrying each agent's instruction file, by date of first commit",
         fontsize=10, color=MUTED)
fig.text(0.02, 0.012, FOOT, fontsize=6.6, color=MUTED)
fig.subplots_adjust(left=0.08, right=0.98, top=0.87, bottom=0.1)
fig.savefig(out / "03-adoption.png", facecolor="white")

# 2. shares by cohort with intervals
rows = [("AGENTS.md (shared)", "AGENTS.md"), ("Claude Code, any", "Claude Code"), ("Claude-specific", None),
        ("Copilot", "Copilot"), ("Cursor", "Cursor"), ("Gemini CLI", "Gemini CLI")]
fig, ax = plt.subplots(figsize=(10, 5.4), dpi=200)
for j, (cohort, color, dy) in enumerate((("established", "#0f172a", -0.17), ("new", "#94a3b8", 0.17))):
    for i, (lab, k) in enumerate(rows[::-1]):
        if k is None:
            v = s["claude_specific"][cohort]; p, (lo, hi) = v["pct"], v["ci"]
        else:
            p = s["share"][cohort][k]; lo, hi = s["ci"][cohort][k]
        ax.barh(i + dy, p, height=0.32, color=color, zorder=2)
        ax.plot([lo, hi], [i + dy, i + dy], color="#f59e0b", lw=1.6, zorder=3)
        ax.text(hi + 0.4, i + dy, f"{p:.1f}%", va="center", fontsize=9, color=INK)
ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], fontsize=10.5, color=INK)
ax.set_xlim(0, 26)
ax.set_xlabel("% of sampled repos (orange = 95% interval)", fontsize=10, color=MUTED)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.tick_params(axis="y", length=0); ax.tick_params(axis="x", colors=MUTED); ax.grid(axis="x", color=GRID, zorder=0)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#0f172a", label="1,200 popular active repos"), Patch(color="#94a3b8", label="1,000 repos created in 2026")],
          loc="lower right", frameon=False, fontsize=10)
fig.text(0.02, 0.96, "Claude Code and the shared AGENTS.md dominate. Cursor barely shows.", fontsize=13.5, weight="bold", color=INK)
fig.text(0.02, 0.915, "Repos carrying each agent's instruction files; a repo can carry several",
         fontsize=10, color=MUTED)
fig.text(0.02, 0.012, "Samples drawn 6 Oct 2026 from GitHub search · 'Claude-specific' excludes CLAUDE.md files that only point to AGENTS.md · "
         "github.com/nazmul284/agent-files-on-github", fontsize=6.6, color=MUTED)
fig.subplots_adjust(left=0.2, right=0.97, top=0.87, bottom=0.13)
fig.savefig(out / "02-shares.png", facecolor="white")
print("ok")
