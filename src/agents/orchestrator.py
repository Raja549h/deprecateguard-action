import json
from typing import List, Dict, Any
from src.agents.detector import DetectorAgent
from src.agents.writer import WriterAgent

class Orchestrator:
    """
    Coordinates the Detector (deterministic) and Writer (LLM) agents.
    """
    def __init__(self):
        self.detector = DetectorAgent()
        self.writer = WriterAgent()
        
    def run_pipeline(self, base_spec: str, revision_spec: str, repo_path: str) -> List[Dict[str, Any]]:
        """
        Runs the full Deprecation Impact Pipeline.
        """
        print("--- STARTING ORCHESTRATOR PIPELINE ---")
        
        # Step 1: Deterministic Detection
        print("[Detector Agent] Running deterministic analysis...")
        impacts = self.detector.run(base_spec, revision_spec, repo_path)
        
        if not impacts:
            print("[Detector Agent] No impacted call-sites found.")
            return [{"status": "SUCCESS", "deprecations": []}]
            
        if impacts and "status" in impacts[0] and impacts[0]["status"] == "PARSE_ERROR":
            print("[Detector Agent] " + impacts[0]["message"])
            return impacts
            
        print(f"[Detector Agent] Found {len(impacts)} impacted call-sites.")
        
        # Step 2: Notice Generation
        print("[Writer Agent] Generating migration notices...")
        final_reports = []
        
        for impact in impacts:
            notice = self.writer.generate_notice(impact)
            
            # Combine the original deterministic data with the LLM-generated notice
            full_report = {
                "technical_details": impact,
                "migration_notice": notice
            }
            final_reports.append(full_report)
            
        print("--- PIPELINE COMPLETE ---")
        return final_reports

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python -m src.agents.orchestrator <base_spec> <revision_spec> <repo_path>")
        sys.exit(1)
        
    base = sys.argv[1]
    rev = sys.argv[2]
    repo = sys.argv[3]
    
    orchestrator = Orchestrator()
    results = orchestrator.run_pipeline(base, rev, repo)
    
    print("\n--- FINAL JSON OUTPUT ---")
    print(json.dumps(results, indent=2))
