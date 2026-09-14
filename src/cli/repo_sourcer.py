import os, json, time, urllib.request
from urllib.error import HTTPError

SDKS = ["stripe", "twilio", "openai", "anthropic", "github", "slack_sdk", "sendgrid", "boto3"]

def fetch_repos(sdk_name):
    url = f"https://api.github.com/search/repositories?q={sdk_name}+language:python+stars:>50&sort=stars&order=desc"
    req = urllib.request.Request(url, headers={"User-Agent": "DeprecateGuard-Corpus"})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())["items"]
    except HTTPError as e:
        if e.code == 403:
            print(f"Rate limited! Waiting 30s before retrying {sdk_name}...")
            time.sleep(30)
            return fetch_repos(sdk_name)
        print(f"Error fetching {sdk_name}: {e}")
        return []
    except Exception as e:
        print(f"Error fetching {sdk_name}: {e}")
        return []

def run_sourcing():
    cache_file = "corpus_candidates.json"
    if os.path.exists(cache_file):
        print("Loading from cache...")
        with open(cache_file, "r") as f: return json.load(f)
    
    candidates = {}
    counts_per_sdk = {s: 0 for s in SDKS}
    
    for sdk in SDKS:
        print(f"Sourcing {sdk}...")
        items = fetch_repos(sdk)
        for repo in items[:20]: # Top 20 per SDK
            if repo["archived"] or repo["fork"]:
                continue
            lic = repo.get("license")
            if lic and lic.get("key") in ["mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "unlicense"]:
                rid = str(repo["id"])
                if rid not in candidates:
                    candidates[rid] = {
                        "repo_id": rid,
                        "repo_url": repo["html_url"],
                        "clone_url": repo["clone_url"],
                        "stars": repo["stargazers_count"],
                        "license": lic["key"],
                        "sdk_detected": [sdk],
                        "last_push": repo["pushed_at"]
                    }
                    counts_per_sdk[sdk] += 1
                else:
                    candidates[rid]["sdk_detected"].append(sdk)
                    counts_per_sdk[sdk] += 1
        time.sleep(3) # Be nice to the API
    
    out = list(candidates.values())
    with open(cache_file, "w") as f: json.dump(out, f, indent=2)
    print("\n=== AUTOMATED REPO SOURCING REPORT ===")
    print(f"Total Unique Repositories Found: {len(out)}")
    for k, v in counts_per_sdk.items():
        print(f" - {k}: {v} candidates")
    return out

if __name__ == "__main__":
    run_sourcing()
