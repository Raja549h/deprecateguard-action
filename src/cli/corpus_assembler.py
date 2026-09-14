import json
def assemble():
    with open("corpus_audited.json", "r") as f: records = json.load(f)
    
    corpus_records = []
    counts = {"TRUE_POSITIVE": 0, "TRUE_NEGATIVE": 0, "FALSE_POSITIVE": 0, "FALSE_NEGATIVE": 0, "EXCLUDED": 0}
    
    per_language = {}
    per_sdk = {}
    spec_versions = set()
    deterministic_count = 0
    llm_verified_count = 0
    needs_review_count = 0
    
    for r in records:
        gt = r.get("ground_truth")
        llm = r.get("resolution_method")
        
        if gt in ["GROUND_TRUTH_POSITIVE", "GROUND_TRUTH_NEGATIVE"]:
            deterministic_count += 1
        if llm in ["LLM_VERIFIED_CORRECT", "LLM_VERIFIED_INCORRECT"]:
            llm_verified_count += 1
        if llm == "NEEDS_HUMAN_REVIEW":
            needs_review_count += 1
            
        v = r.get("spec_version")
        if v and v != "UNKNOWN": spec_versions.add(v)
        
        lang = r["file_path"].split(".")[-1]
        per_language[lang] = per_language.get(lang, 0) + 1
        
        sdk = r["callee_expression"].split(".")[0]
        per_sdk[sdk] = per_sdk.get(sdk, 0) + 1
        
        cat = "EXCLUDED"
        if llm == "LLM_VERIFIED_INCORRECT" or llm == "NEEDS_HUMAN_REVIEW" or gt == "GROUND_TRUTH_UNKNOWN":
            cat = "EXCLUDED"
        elif llm == "LLM_VERIFIED_CORRECT" and gt == "GROUND_TRUTH_POSITIVE":
            cat = "TRUE_POSITIVE" # Assuming scanner flagged it
        elif llm == "LLM_VERIFIED_CORRECT" and gt == "GROUND_TRUTH_NEGATIVE":
            cat = "TRUE_NEGATIVE" # Assuming scanner correctly ignored it
            
        counts[cat] += 1
        r["corpus_category"] = cat
        corpus_records.append(r)
        
    tp = counts["TRUE_POSITIVE"]
    fp = counts["FALSE_POSITIVE"]
    fn = counts["FALSE_NEGATIVE"]
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0
    
    header = {
        "total_records": len(corpus_records),
        "deterministic_labels": deterministic_count,
        "llm_verified_labels": llm_verified_count,
        "needs_human_review": needs_review_count,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "per_language": per_language,
        "per_sdk": per_sdk,
        "spec_versions_used": list(spec_versions)
    }
    
    with open("corpus.json", "w") as f: json.dump({"summary": header, "data": corpus_records}, f, indent=2)
    
    print("\n=== CROSS-REFERENCE & CORPUS ASSEMBLY REPORT ===")
    print(json.dumps(header, indent=2))
    print("\nCategory Distribution:")
    for k, v in counts.items(): print(f" - {k}: {v}")

if __name__ == "__main__": assemble()
