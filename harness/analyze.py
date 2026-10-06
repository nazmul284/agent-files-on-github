"""Turn data/scan.jsonl + data/dates.json into results/summary.json.

Signals (a repo can carry several):
  Claude Code   CLAUDE.md at root, .claude/CLAUDE.md, or a .claude/ directory
  AGENTS.md     AGENTS.md at root (read by Codex and 20+ other tools; not one vendor's file)
  Cursor        .cursor/rules/ or legacy .cursorrules
  Copilot       .github/copilot-instructions.md or .github/instructions/
  Gemini CLI    GEMINI.md at root or a .gemini/ directory
  Windsurf      .windsurfrules or .windsurf/
  Cline         .clinerules
"""
import json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
recs = [json.loads(l) for l in (ROOT / "data" / "scan.jsonl").open()]
dates = json.loads((ROOT / "data" / "dates.json").read_text()) if (ROOT / "data" / "dates.json").exists() else {}
ok = [r for r in recs if r["status"] == 200]

def signals(r):
    f, d = r["files"], r["dirs"]
    gh = d.get(".github", [])
    s = {
        "Claude Code": "CLAUDE.md" in f or ".claude" in d,
        "Claude Code (CLAUDE.md)": "CLAUDE.md" in f or "CLAUDE.md" in d.get(".claude", []),
        "AGENTS.md": "AGENTS.md" in f,
        "Cursor": ".cursor/rules" in d or ".cursorrules" in f,
        "Copilot": "copilot-instructions.md" in gh or ".github/instructions" in d,
        "Gemini CLI": "GEMINI.md" in f or ".gemini" in d,
        "Windsurf": ".windsurfrules" in f or ".windsurf" in d,
        "Cline": ".clinerules" in f or ".clinerules" in d,
    }
    s["any agent file"] = any(v for k, v in s.items() if k != "Claude Code (CLAUDE.md)")
    return s

out = {"n": {}, "share": {}, "combos": {}, "claude_md_kind": {}, "dot_claude_contents": {}, "by_language": {}}
for cohort in ("established", "new"):
    rs = [r for r in ok if r["cohort"] == cohort]
    out["n"][cohort] = {"sampled": sum(r["cohort"] == cohort for r in recs), "readable": len(rs)}
    sig = [signals(r) for r in rs]
    keys = list(sig[0])
    out["share"][cohort] = {k: round(100 * sum(s[k] for s in sig) / len(rs), 1) for k in keys}
    out["share"][cohort]["_counts"] = {k: sum(s[k] for s in sig) for k in keys}
    main = ["Claude Code", "AGENTS.md", "Cursor", "Copilot", "Gemini CLI"]
    out["combos"][cohort] = Counter("+".join(k for k in main if s[k]) or "none" for s in sig).most_common(12)
    # how CLAUDE.md files relate to AGENTS.md
    kinds = Counter()
    for r in rs:
        c = r["files"].get("CLAUDE.md")
        if not c:
            continue
        txt = c.get("small_text")
        if c.get("symlink"):
            kinds["symlink to AGENTS.md" if "agents.md" in c.get("target", "").lower() else "symlink to other file"] += 1
        elif txt is not None and re.search(r"agents\.md", txt, re.I):
            # widened after reading the short files: prose pointers ("Read and follow AGENTS.md")
            # and path imports (@./AGENTS.md) count, not just a bare @AGENTS.md
            kinds["short pointer to AGENTS.md (import or prose)"] += 1
        elif txt is not None:
            kinds["short file, other content"] += 1
        else:
            kinds["full file (400+ bytes)"] += 1
    out["claude_md_kind"][cohort] = dict(kinds)
    out["dot_claude_contents"][cohort] = Counter(x for r in rs for x in r["dirs"].get(".claude", [])).most_common(12)
    langs = Counter(r["language"] for r in rs)
    out["by_language"][cohort] = {l: {"n": n, "claude": round(100 * sum(signals(r)["Claude Code"] for r in rs if r["language"] == l) / n, 1),
                                      "agents_md": round(100 * sum(signals(r)["AGENTS.md"] for r in rs if r["language"] == l) / n, 1)}
                                  for l, n in langs.most_common(8) if l}
# adoption over time: share of all readable sampled repos (both cohorts) whose file existed by each month-end
PATHS = {"Claude Code (CLAUDE.md)": "CLAUDE.md", "AGENTS.md": "AGENTS.md", "Cursor (.cursor/rules)": ".cursor/rules",
         "Cursor (.cursorrules)": ".cursorrules", "Copilot": ".github/copilot-instructions.md", "Gemini CLI": "GEMINI.md"}
months = [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13) if f"{y}-{m:02d}" <= "2026-09"]
est = [r for r in ok if r["cohort"] == "established"]
out["adoption_established"] = {lab: [round(100 * sum(1 for r in est if (dates.get(r["repo"], {}).get(p) or "9999") <= m + "-31") / len(est), 2)
                                     for m in months] for lab, p in PATHS.items()}
out["months"] = months
# Claude-specific setup: a CLAUDE.md that is not a pointer to AGENTS.md, or a non-empty .claude/ directory
def claude_specific(r):
    c = r["files"].get("CLAUDE.md")
    own = bool(c) and not ((c.get("symlink") and "agents.md" in c.get("target", "").lower()) or
                           (c.get("small_text") is not None and re.search(r"agents\.md", c["small_text"], re.I)))
    return own or bool(r["dirs"].get(".claude"))
import math
def wilson(k, n):
    z = 1.96; p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]
out["claude_specific"] = {}; out["ci"] = {}
for cohort in ("established", "new"):
    rs = [r for r in ok if r["cohort"] == cohort]
    k = sum(claude_specific(r) for r in rs)
    out["claude_specific"][cohort] = {"k": k, "pct": round(100 * k / len(rs), 1), "ci": wilson(k, len(rs))}
    out["ci"][cohort] = {key: wilson(cnt, len(rs)) for key, cnt in out["share"][cohort]["_counts"].items()}
(ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=2))
print(json.dumps({k: out[k] for k in ("n", "share", "claude_md_kind")}, indent=1))
