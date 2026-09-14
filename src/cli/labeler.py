import os, json, urllib.request, re
from datetime import datetime

def download_spec(url, sdk_name):
    cache_path = f"spec_cache_{sdk_name}.json"
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f: return json.load(f)
    # Only JSON specs are supported for this MVP without PyYAML
    if not url.endswith(".json"):
        return {"info": {"version": "UNKNOWN"}, "paths": {}}
    try:
        print(f"Downloading spec for {sdk_name}...")
        req = urllib.request.Request(url, headers={"User-Agent": "DeprecateGuard"})
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            with open(cache_path, "w") as f: json.dump(data, f)
            return data
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return {"info": {"version": "UNKNOWN"}, "paths": {}}

def run_labeler():
    with open("corpus_extractions.json", "r") as f: extractions = json.load(f)
    with open("src/cli/sdk_registry.json", "r") as f: registry = json.load(f)
    
    sdk_map = {entry["endpoint_template"]: {"name": entry["sdk_name"], "url": entry["source_url"]} for entry in registry}
    
    specs = {}
    for ep, meta in sdk_map.items():
        if meta["name"] not in specs:
            specs[meta["name"]] = download_spec(meta["url"], meta["name"])
            
    labeled_records = []
    stats = {"GROUND_TRUTH_POSITIVE": 0, "GROUND_TRUTH_NEGATIVE": 0, "GROUND_TRUTH_UNKNOWN": 0}
    
    for rec in extractions.get("records", []):
        ep = rec["resolved_endpoint"]
        method = rec["http_method"].lower()
        meta = sdk_map.get(ep)
        
        if not meta:
            rec["ground_truth"] = "GROUND_TRUTH_UNKNOWN"
            rec["ground_truth_reason"] = "ENDPOINT_NOT_IN_REGISTRY"
        else:
            spec = specs[meta["name"]]
            # Extract path from URL (e.g. https://api.stripe.com/v1/charges -> /v1/charges)
            match = re.search(r"https?://[^/]+(/.*)", ep)
            path = match.group(1) if match else ep
            
            # Handle path templating differences (e.g. {id} vs {charge}) - simple fallback for MVP
            paths_obj = spec.get("paths", {})
            op = None
            if path in paths_obj:
                op = paths_obj[path].get(method)
            
            rec["spec_version"] = spec.get("info", {}).get("version", "UNKNOWN")
            rec["spec_retrieved_date"] = datetime.utcnow().date().isoformat()
            
            if not op:
                rec["ground_truth"] = "GROUND_TRUTH_UNKNOWN"
                rec["ground_truth_reason"] = "ENDPOINT_NOT_IN_SPEC"
            elif op.get("deprecated", False):
                rec["ground_truth"] = "GROUND_TRUTH_POSITIVE"
                rec["ground_truth_confidence"] = "DETERMINISTIC"
            else:
                rec["ground_truth"] = "GROUND_TRUTH_NEGATIVE"
                rec["ground_truth_confidence"] = "DETERMINISTIC"
                
        stats[rec["ground_truth"]] += 1
        labeled_records.append(rec)

    with open("corpus_labeled.json", "w") as f:
        json.dump(labeled_records, f, indent=2)
        
    print("\n=== DETERMINISTIC DEPRECATION LABELING REPORT ===")
    print(f"Total Records Labeled: {len(labeled_records)}")
    for k, v in stats.items():
        print(f" - {k}: {v}")

if __name__ == "__main__":
    run_labeler()
