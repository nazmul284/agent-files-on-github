"""For every sampled repo, record which AI coding agent instruction files exist.

Checks the root tree, then .github/, .cursor/ and .claude/ when present. Records symlinks,
and reads small CLAUDE.md / AGENTS.md files to catch one-line imports (@AGENTS.md).
Writes data/scan.jsonl (one line per repo). Resumable: API responses are cached.
"""
import base64, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from gh import get

ROOT = Path(__file__).resolve().parent.parent
sample = json.loads((ROOT / "data" / "sample.json").read_text())
ROOT_FILES = ["CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".windsurfrules", ".clinerules",
              "CLAUDE.local.md", "AGENT.md", "copilot-instructions.md"]
ROOT_DIRS = [".claude", ".cursor", ".github", ".windsurf", ".gemini", ".codex", ".clinerules", ".kiro", ".junie", ".agents"]

def key(repo, what):
    return repo.replace("/", "__") + "__" + what

def subtree(repo, sha, name):
    r = get(f"repos/{repo}/git/trees/{sha}", key(repo, name))
    return {e["path"]: e for e in (r["json"] or {}).get("tree", [])} if r["status"] == 200 else {}

def small_text(repo, entry, name):
    if entry.get("type") != "blob" or entry.get("size", 10**9) > 400:
        return None
    r = get(f"repos/{repo}/git/blobs/{entry['sha']}", key(repo, "blob_" + name))
    if r["status"] != 200:
        return None
    return base64.b64decode(r["json"]["content"]).decode("utf-8", "replace")

def scan(item):
    cohort, repo, meta = item
    r = get(f"repos/{repo}/git/trees/{meta['branch']}", key(repo, "root"))
    rec = {"repo": repo, "cohort": cohort, **meta, "status": r["status"]}
    if r["status"] != 200:
        return rec
    root = {e["path"]: e for e in r["json"]["tree"]}
    files = {}
    for f in ROOT_FILES:
        if f in root:
            e = root[f]
            files[f] = {"type": e["type"], "symlink": e.get("mode") == "120000", "size": e.get("size")}
            if e.get("mode") == "120000":       # symlink: blob content is the target path
                t = get(f"repos/{repo}/git/blobs/{e['sha']}", key(repo, "link_" + f))
                if t["status"] == 200:
                    files[f]["target"] = base64.b64decode(t["json"]["content"]).decode().strip()
            elif f in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
                txt = small_text(repo, e, f)
                if txt is not None:
                    files[f]["small_text"] = txt[:400]
    dirs = {}
    for d in ROOT_DIRS:
        if d in root and root[d]["type"] == "tree":
            kids = subtree(repo, root[d]["sha"], d.strip("."))
            dirs[d] = sorted(kids)
            if d == ".github":
                for sub in ("instructions", "agents", "prompts", "chatmodes"):
                    if sub in kids and kids[sub]["type"] == "tree":
                        dirs[".github/" + sub] = sorted(subtree(repo, kids[sub]["sha"], "github_" + sub))
            if d == ".cursor" and "rules" in kids and kids["rules"]["type"] == "tree":
                dirs[".cursor/rules"] = sorted(subtree(repo, kids["rules"]["sha"], "cursor_rules"))
    rec.update(files=files, dirs=dirs, truncated=r["json"].get("truncated", False))
    return rec

items = [(c, repo, meta) for c, v in sample.items() for repo, meta in v["repos"].items()]
print(len(items), "repos", flush=True)
done = 0
with (ROOT / "data" / "scan.jsonl").open("w") as out, ThreadPoolExecutor(4) as ex:
    for rec in ex.map(scan, items):
        out.write(json.dumps(rec) + "\n"); done += 1
        if done % 100 == 0:
            print(f"  scanned {done}/{len(items)}", flush=True)
print("done", flush=True)
