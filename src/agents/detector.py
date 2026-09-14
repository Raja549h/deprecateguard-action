from typing import List, Dict, Any
from src.detector.core import analyze_deprecation_impact

class DetectorAgent:
    """
    Deterministic agent that runs oasdiff and tree-sitter.
    No LLM is used here. 
    """
    
    def __init__(self):
        pass
        
    def run(self, base_spec: str, revision_spec: str, repo_path: str) -> List[Dict[str, Any]]:
        """
        Executes the detection pipeline.
        Returns a list of impacted call-sites.
        """
        # Call the core logic we built in Phase 1
        return analyze_deprecation_impact(base_spec, revision_spec, repo_path)
