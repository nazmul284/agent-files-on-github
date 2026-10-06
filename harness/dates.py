"""First-commit date of each agent instruction file found by scan.py.

GET commits?path=<file>&per_page=1 returns newest first; the Link header's rel="last"
page is the oldest commit. Two calls per file. Writes data/dates.json.
Caveat: only files still present today are seen, and history follows the default branch.
"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from gh import get

ROOT = Path(__file__).resolve().parent.parent
PATHS = {"CLAUDE.md": lambda r: "CLAUDE.md" in r["files"],
         "AGENTS.md": lambda r: "AGENTS.md" in r["files"],
         "GEMINI.md": lambda r: "GEMINI.md" in r["files"],
         ".cursorrules": lambda r: ".cursorrules" in r["files"],
         ".cursor/rules": lambda r: ".cursor/rules" in r["dirs"],
         ".github/copilot-instructions.md": lambda r: "copilot-instructions.md" in r["dirs"].get(".github", []),
         ".windsurfrules": lambda r: ".windsurfrules" in r["files"],
         ".claude": lambda r: ".claude" in r["dirs"]}
recs = [json.loads(l) for l in (ROOT / "data" / "scan.jsonl").open()]
jobs = [(r["repo"], p) for r in recs if r["status"] == 200 for p, f in PATHS.items() if f(r)]
print(len(jobs), "files to date", flush=True)

def first(job):
    repo, path = job
    k = repo.replace("/", "__") + "__c_" + path.replace("/", "_")
    r = get(f"repos/{repo}/commits?path={path}&per_page=1", k)
    if r["status"] != 200 or not r["json"]:
        return repo, path, None
    m = re.search(r'[?&]page=(\d+)>; rel="last"', r["headers"].get("link", ""))
    if m:
        r = get(f"repos/{repo}/commits?path={path}&per_page=1&page={m[1]}", k + "_last")
        if r["status"] != 200 or not r["json"]:
            return repo, path, None
    return repo, path, r["json"][0]["commit"]["committer"]["date"][:10]

out = {}
with ThreadPoolExecutor(4) as ex:
    for i, (repo, path, d) in enumerate(ex.map(first, jobs), 1):
        out.setdefault(repo, {})[path] = d
        if i % 100 == 0:
            print(f"  dated {i}/{len(jobs)}", flush=True)
(ROOT / "data" / "dates.json").write_text(json.dumps(out, indent=1))
print("done", flush=True)
