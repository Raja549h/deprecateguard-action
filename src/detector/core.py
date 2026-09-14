import os
import glob
from typing import List, Dict, Any
from src.detector.oasdiff import run_oasdiff, extract_deprecated_endpoints
from src.detector.ast_parser import find_api_calls_in_file

def analyze_deprecation_impact(base_spec: str, revision_spec: str, repo_path: str) -> List[Dict[str, Any]]:
    """
    Main orchestration logic for Phase 1.
    1. Runs oasdiff to find deprecated endpoints
    2. Parses the repo to find API calls
    3. Cross-references them and returns impacted call-sites
    """
    print(f"Running oasdiff between {base_spec} and {revision_spec}...")
    try:
        changes = run_oasdiff(base_spec, revision_spec, command="changelog")
    except ValueError as e:
        print(f"Failed to parse OpenAPI specs: {e}")
        return [{"status": "PARSE_ERROR", "message": str(e)}]
        
    deprecated_endpoints = extract_deprecated_endpoints(changes)
    
    print(f"Found {len(deprecated_endpoints)} deprecated endpoints.")
    for dep in deprecated_endpoints:
        print(f" - {dep['method']} {dep['path']}")
        
    print(f"\nScanning repository at {repo_path}...")
    impacted_calls = []
    
    # Simple recursive glob for python files
    search_pattern = os.path.join(repo_path, "**", "*.py")
    files = glob.glob(search_pattern, recursive=True)
    
    for filepath in files:
        calls = find_api_calls_in_file(filepath)
        for call in calls:
            # Check if this call matches any deprecated endpoint
            for dep in deprecated_endpoints:
                if call["method"] == dep["method"] and dep["path"] in call["url"]:
                    impacted_calls.append({
                        "file": filepath,
                        "line": call["line"],
                        "url": call["url"],
                        "method": call["method"],
                        "reason": dep["reason"]
                    })
                    
    return impacted_calls

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python core.py <base_spec> <revision_spec> <repo_path>")
        sys.exit(1)
        
    base = sys.argv[1]
    rev = sys.argv[2]
    repo = sys.argv[3]
    
    impacts = analyze_deprecation_impact(base, rev, repo)
    print("\n--- DEPRECATION IMPACT REPORT ---")
    if not impacts:
        print("No impacted call-sites found.")
    else:
        for impact in impacts:
            print(f"File: {impact['file']}:{impact['line']}")
            print(f"Call: {impact['method']} {impact['url']}")
            print(f"Reason: {impact['reason']}")
            print("-" * 30)
