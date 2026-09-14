import json
from src.cli.multi_extractor import MultiLanguageExtractor
from src.cli.sarif_emitter import generate_sarif
from src.cli.pr_commenter import generate_pr_comment

def run_test():
    extractor = MultiLanguageExtractor("py")
    with open("fixtures/test_collision.py", "rb") as f: code = f.read()
    calls = extractor.scan_code(code, "fixtures/test_collision.py")
    
    records = []
    from dataclasses import asdict
    for c in calls:
        d = asdict(c)
        d["file_path"] = d["file"]
        d["line_number"] = d["line"]
        d["ground_truth"] = "GROUND_TRUTH_POSITIVE"
        d["ground_truth_confidence"] = "DETERMINISTIC"
        if "twilio" in d["callee_expression"]: d["spec_version"] = "1.0.0"
        if "anthropic" in d["callee_expression"]: d["spec_version"] = "2026-09-14-sha256-a1b2c3d4" # simulated real missing version derive fallback
        records.append(d)
        
    generate_sarif(records, "test_output_collision.sarif")
    generate_pr_comment(records)
    
if __name__ == "__main__": run_test()
