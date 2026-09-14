import json
def calculate_drift():
    try:
        with open("corpus_previous.json", "r") as f: prev = json.load(f)["data"]
    except FileNotFoundError:
        print("No previous corpus found. Baseline established.")
        return
        
    with open("corpus.json", "r") as f: curr = json.load(f)["data"]
    
    prev_map = {f"{r['repo_id']}:{r['file_path']}:{r['line_number']}": r for r in prev}
    curr_map = {f"{r['repo_id']}:{r['file_path']}:{r['line_number']}": r for r in curr}
    
    drift_stats = {"spec_changed": 0, "code_changed": 0, "resolution_changed": 0, "total_drift": 0}
    
    for key, c_rec in curr_map.items():
        if key in prev_map:
            p_rec = prev_map[key]
            drifted = False
            if p_rec.get("ground_truth") != c_rec.get("ground_truth"):
                drift_stats["spec_changed"] += 1
                drifted = True
            if p_rec.get("llm_audit_verdict") != c_rec.get("llm_audit_verdict"):
                drift_stats["resolution_changed"] += 1
                drifted = True
            if p_rec.get("commit_hash") != c_rec.get("commit_hash"):
                # This is just a commit update, real code change drift 
                # would be if the line vanished or changed expression.
                pass
            if drifted:
                drift_stats["total_drift"] += 1
        else:
            drift_stats["code_changed"] += 1 # New call site
            drift_stats["total_drift"] += 1
            
    for key in prev_map:
        if key not in curr_map:
            drift_stats["code_changed"] += 1 # Removed call site
            drift_stats["total_drift"] += 1
            
    report = f"""
## Corpus Drift Report
- **Total Drifted Records:** {drift_stats["total_drift"]}
- **Drift due to OpenAPI Spec updates:** {drift_stats["spec_changed"]}
- **Drift due to Scanner Resolution changes:** {drift_stats["resolution_changed"]}
- **Drift due to Client Source Code changes:** {drift_stats["code_changed"]}
"""
    with open("README.md", "a") as f: f.write(f"\n{report}")
    print("\n=== CONTINUOUS RE-VALIDATION REPORT ===")
    print(report.strip())

if __name__ == "__main__": calculate_drift()
