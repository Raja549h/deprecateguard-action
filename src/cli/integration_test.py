import json, os
from src.cli.sarif_emitter import generate_sarif
from src.cli.pr_commenter import generate_pr_comment

def run_test():
    # We use our previously built corpus_audited.json (which has the real Stripe/Twilio calls).
    with open("corpus_audited.json", "r") as f: records = json.load(f)
    
    # Force a couple of them to be positive so the reporters trigger
    for r in records:
        if "stripe.Charge.create" in r["callee_expression"]:
            r["ground_truth"] = "GROUND_TRUTH_POSITIVE"
            r["ground_truth_confidence"] = "DETERMINISTIC"
        elif "client.messages.create" in r["callee_expression"] and "anthropic" not in r["callee_expression"]:
            r["ground_truth"] = "GROUND_TRUTH_POSITIVE"
            r["ground_truth_confidence"] = "HEURISTIC"
            
    print("Generating SARIF...")
    sarif = generate_sarif(records, "test_output.sarif")
    print("SARIF Generated.")
    
    print("Generating PR Comment...")
    comment = generate_pr_comment(records)
    print("PR Comment Generated.")
    
if __name__ == "__main__": run_test()
