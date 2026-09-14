import json, sys
def generate_queue():
    with open("corpus.json", "r") as f: corpus = json.load(f)
    total = corpus["summary"]["total_records"]
    records = corpus["data"]
    
    needs_review = [r for r in records if r.get("resolution_method") == "NEEDS_HUMAN_REVIEW"]
    
    queue = []
    for r in needs_review:
        queue.append({
            "file": f"{r['file_path']}:{r['line_number']}",
            "snippet": r["callee_expression"], # Mock snippet since we didnt store the raw line in corpus.json
            "claimed_resolution": r["resolved_endpoint"],
            "llm_reasoning": r.get("llm_audit_reason", "No reason provided"),
            "human_decision": "[ ACCEPT / REJECT ]"
        })
        
    with open("needs_review.json", "w") as f: json.dump(queue, f, indent=2)
    
    percentage = (len(needs_review) / total * 100) if total > 0 else 0
    print("\n=== HUMAN REVIEW QUEUE ===")
    print(f"Total Records: {total}")
    print(f"Needs Review: {len(needs_review)} ({percentage:.1f}%)")
    
    if percentage > 15.0:
        print("CRITICAL ERROR: Review threshold exceeded 15%. Pipeline accuracy is too low to ship.")
        sys.exit(1)
    else:
        print("Status: Threshold PASSED. Human review queue generated successfully.")

if __name__ == "__main__": generate_queue()
