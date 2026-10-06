"""Tiny GitHub REST client: token from `gh auth token`, waits out the rate limit, caches JSON."""
import json, subprocess, time, urllib.error, urllib.request
from pathlib import Path

TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

def get(path, cache_key=None, raw=False):
    f = CACHE / (cache_key + ".json") if cache_key else None
    if f and f.exists():
        return json.loads(f.read_text())
    url = "https://api.github.com/" + path
    for attempt in range(8):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}",
                                                   "Accept": "application/vnd.github+json",
                                                   "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = {"status": r.status, "headers": {"link": r.headers.get("Link", "")},
                        "json": json.load(r)}
                if int(r.headers.get("X-RateLimit-Remaining", "100")) < 20:
                    wait = int(r.headers.get("X-RateLimit-Reset", time.time() + 60)) - time.time() + 5
                    print(f"  rate limit low, sleeping {int(wait)}s", flush=True)
                    time.sleep(max(wait, 5))
                break
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
                wait = int(e.headers.get("X-RateLimit-Reset", time.time() + 60)) - time.time() + 5
                print(f"  rate limited, sleeping {int(wait)}s", flush=True)
                time.sleep(max(wait, 5)); continue
            if e.code in (404, 409, 451):        # gone, empty repo, blocked
                body = {"status": e.code, "headers": {}, "json": None}; break
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    else:
        body = {"status": -1, "headers": {}, "json": None}
    if f:
        f.write_text(json.dumps(body))
    return body
