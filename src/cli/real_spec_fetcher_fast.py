import urllib.request, json, hashlib, datetime, sys

def get_real_spec_version(url):
    print(f"Fetching {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "DeprecateGuard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read(1000000).decode("utf-8") # only read first 1MB to find version!
    except Exception as e:
        print(f"Fetch failed: {e}")
        return "UNKNOWN"
        
    version = None
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith('"version":') or line.startswith('version:'):
            # parse out the actual version string
            version = line.split(":", 1)[1].strip().strip('"').strip("'").strip('",')
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
    twilio_ver = get_real_spec_version("https://raw.githubusercontent.com/twilio/twilio-oai/main/spec/yaml/twilio_api_v2010.yaml")
    stripe_ver = get_real_spec_version("https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json")
    
    with open("real_spec_versions.json", "w") as f: 
        json.dump({"twilio": twilio_ver, "stripe": stripe_ver}, f)
