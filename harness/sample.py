"""Draw random samples of GitHub repos for two cohorts.

  established: stars > 1000, pushed since 2026-09-06, not forks/archived
  new:         created since 2026-01-01, stars > 100, not forks/archived

GitHub search returns at most 1,000 results per query, so each cohort's star range is
split until every slice fits, every slice is listed in full, and the sample is drawn
uniformly from the union. Writes data/sample.json.
"""
import json, random, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COHORTS = {"established": ("pushed:>=2026-09-06 fork:false archived:false", 1001, 600000, 1200),
           "new": ("created:>=2026-01-01 fork:false archived:false", 101, 600000, 1000)}

def search(q, page=1):
    for attempt in range(6):
        r = subprocess.run(["gh", "api", "-X", "GET", "search/repositories", "-f", f"q={q}",
                            "-f", "per_page=100", "-f", f"page={page}", "-f", "sort=stars"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            time.sleep(2.1)                      # search limit: 30 requests a minute
            return json.loads(r.stdout)
        print("  retry", attempt + 1, r.stderr[:120], flush=True)
        time.sleep(20 * (attempt + 1))
    raise SystemExit("search failed: " + q)

def slices(base, lo, hi):
    n = search(f"{base} stars:{lo}..{hi}")["total_count"]
    if n <= 1000 or lo == hi:
        return [(lo, hi, n)]
    mid = (lo + hi) // 2 if hi - lo > 2000 else lo + max(1, (hi - lo) // 2)
    return slices(base, lo, mid) + slices(base, mid + 1, hi)

out = {}
for name, (base, lo, hi, k) in COHORTS.items():
    parts = slices(base, lo, hi)
    total = sum(n for *_, n in parts)
    print(name, len(parts), "slices,", total, "repos", flush=True)
    repos = {}
    for a, b, n in parts:
        for page in range(1, min(10, -(-n // 100)) + 1):
            for it in search(f"{base} stars:{a}..{b}", page)["items"]:
                repos[it["full_name"]] = {"stars": it["stargazers_count"], "created": it["created_at"][:10],
                                          "pushed": it["pushed_at"][:10], "branch": it["default_branch"],
                                          "language": it["language"]}
        print(f"  {name} stars {a}..{b}: listed {len(repos)} so far", flush=True)
    rng = random.Random(20261006)
    pick = sorted(rng.sample(sorted(repos), min(k, len(repos))))
    out[name] = {"population_listed": len(repos), "population_reported": total,
                 "repos": {r: repos[r] for r in pick}}
(ROOT / "data" / "sample.json").write_text(json.dumps(out, indent=1))
print("done", {k: len(v["repos"]) for k, v in out.items()})
