import json
def generate_sarif(findings, output_file="deprecateguard.sarif"):
    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "DeprecateGuard",
                    "informationUri": "https://deprecateguard.com",
                    "rules": []
                }
            },
            "results": []
        }]
    }
    
    rule_map = set()
    results = []
    rules = []
    
    for f in findings:
        if f.get("ground_truth") == "GROUND_TRUTH_NEGATIVE":
            continue
            
        spec_version = f.get("spec_version", "UNKNOWN")
        if spec_version == "UNKNOWN":
            ce = f["callee_expression"]
            print(f"Suppressing finding for {ce} due to UNKNOWN spec version.")
            continue
            
        canon = f.get("canonical_method", f["callee_expression"]).upper().replace(".", "-")
        rule_id = f"DG-{canon}"
        ep = f["resolved_endpoint"]
        
        if rule_id not in rule_map:
            rules.append({"id": rule_id, "shortDescription": {"text": f"Deprecated API Call: {ep}"}})
            rule_map.add(rule_id)
            
        ce = f["callee_expression"]
        msg = f"Call to deprecated endpoint {ep} via SDK method {ce}."
        
        res = {
            "ruleId": rule_id,
            "level": "warning",
            "message": {"text": msg},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f["file_path"]},
                    "region": {"startLine": f["line_number"]}
                }
            }],
            "properties": {
                "spec_version": spec_version,
                "confidence": f.get("ground_truth_confidence", "HEURISTIC")
            }
        }
        results.append(res)
        
    sarif["runs"][0]["tool"]["driver"]["rules"] = rules
    sarif["runs"][0]["results"] = results
    
    with open(output_file, "w") as out:
        json.dump(sarif, out, indent=2)
    return sarif
