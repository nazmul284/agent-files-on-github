"""Fixed-width tables from results/summary.json."""
import json
from pathlib import Path
s = json.loads((Path(__file__).resolve().parent.parent / "results" / "summary.json").read_text())
E, N = "established", "new"
pct = lambda c, k: s["share"][c][k]
ci = lambda c, k: s["ci"][c][k]

print("Share of repos with each agent's instruction files, %\n")
print(f"{'':24}{'established':>13}{'95% CI':>13}{'new':>8}{'95% CI':>13}")
print(f"{'':24}{s['n'][E]['readable']:>13,}{'':>13}{s['n'][N]['readable']:>8,}")
print(f"{'-'*23:24}{'-'*11:>13}{'-'*11:>13}{'-'*5:>8}{'-'*11:>13}")
rows = [("any agent file", "any agent file"), ("AGENTS.md (shared)", "AGENTS.md"),
        ("Claude Code, any", "Claude Code"), ("Claude-specific", None), ("Copilot", "Copilot"),
        ("Cursor", "Cursor"), ("Gemini CLI", "Gemini CLI"), ("Windsurf", "Windsurf"), ("Cline", "Cline")]
for lab, k in rows:
    if k is None:
        e, n = s["claude_specific"][E], s["claude_specific"][N]
        vals = (e["pct"], e["ci"], n["pct"], n["ci"])
    else:
        vals = (pct(E, k), ci(E, k), pct(N, k), ci(N, k))
    f = lambda c: f"{c[0]}-{c[1]}"
    print(f"{lab:24}{vals[0]:>13}{f(vals[1]):>13}{vals[2]:>8}{f(vals[3]):>13}")

print("\n\nWhat the root CLAUDE.md file actually is\n")
K = [("full file (400+ bytes)", "own instructions, 400+ bytes"), ("short pointer to AGENTS.md (import or prose)", "short pointer to AGENTS.md"),
     ("symlink to AGENTS.md", "symlink to AGENTS.md"), ("short file, other content", "short, other"), ("symlink to other file", "symlink, other")]
tot = {c: sum(s["claude_md_kind"][c].values()) for c in (E, N)}
print(f"{'':30}{'established':>13}{'new':>8}")
print(f"{'':30}{tot[E]:>13}{tot[N]:>8}")
print(f"{'-'*29:30}{'-'*11:>13}{'-'*5:>8}")
for k, lab in K:
    print(f"{lab:30}{s['claude_md_kind'][E].get(k, 0):>13}{s['claude_md_kind'][N].get(k, 0):>8}")
ptr = {c: s["claude_md_kind"][c].get("short pointer to AGENTS.md (import or prose)", 0) + s["claude_md_kind"][c].get("symlink to AGENTS.md", 0) for c in (E, N)}
print(f"{'pointer to AGENTS.md, %':30}{round(100*ptr[E]/tot[E]):>13}{round(100*ptr[N]/tot[N]):>8}")

print("\n\nWhat is inside .claude/ folders (repos)\n")
d = dict(s["dot_claude_contents"][E]); dn = dict(s["dot_claude_contents"][N])
print(f"{'':20}{'established':>13}{'new':>8}")
print(f"{'-'*19:20}{'-'*11:>13}{'-'*5:>8}")
for k in ["skills", "settings.json", "agents", "commands", "rules", "hooks", "CLAUDE.md"]:
    print(f"{k:20}{d.get(k, 0):>13}{dn.get(k, 0):>8}")

print("\n\nEstablished repos by main language, %\n")
print(f"{'language':12}{'repos':>7}{'Claude Code':>13}{'AGENTS.md':>11}")
print(f"{'-'*11:12}{'-'*5:>7}{'-'*11:>13}{'-'*9:>11}")
for l, v in s["by_language"][E].items():
    print(f"{l:12}{v['n']:>7}{v['claude']:>13}{v['agents_md']:>11}")

print("\n\nWhich files a repo carries together (repos)\n")
names = {"none": "no agent file"}
ce, cn = dict(map(tuple, s["combos"][E])), dict(map(tuple, s["combos"][N]))
keys = [k for k, _ in s["combos"][E] if k != "none"][:6]
print(f"{'combination':34}{'established':>13}{'new':>8}")
print(f"{'-'*33:34}{'-'*11:>13}{'-'*5:>8}")
for k in keys:
    lab = k.replace("Claude Code", "Claude").replace("+", " + ")
    print(f"{lab:34}{ce.get(k, 0):>13}{cn.get(k, 0):>8}")
