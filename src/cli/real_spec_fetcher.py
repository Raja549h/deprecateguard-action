import urllib.request, json, hashlib, datetime, sys

def get_real_spec_version(url):
    print(f"Fetching {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "DeprecateGuard-Fetcher/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Fetch failed: {e}")
        return "UNKNOWN"
    
    version = None
    if url.endswith(".json"):
        try:
            data = json.loads(content)
            version = data.get("info", {}).get("version")
        except: pass
    else:
        # Naive YAML extraction for info.version without pyyaml dependency
        for line in content.split("\n"):
            if line.strip().startswith("version:"): 
                version = line.split(":", 1)[1].strip().strip('"').strip("'")
                break
    
    if version:
        print(f"Found explicit version: {version}")
        return version
    else:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        derived = f"{today}-sha256-{content_hash}"
        print(f"No version found. Derived from hash: {derived}")
        return derived

if __name__ == "__main__":
    print("Testing Twilio...")
    twilio_ver = get_real_spec_version("https://raw.githubusercontent.com/twilio/twilio-oai/main/spec/yaml/twilio_api_v2010.yaml")
    
    print("\nTesting GitHub...")
    github_ver = get_real_spec_version("https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json")
    
    # Write versions to disk so integration_test_v2 can use them!
    with open("real_spec_versions.json", "w") as f:
        json.dump({"twilio": twilio_ver, "github": github_ver}, f)
