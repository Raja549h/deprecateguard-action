import subprocess
import json
import os
from typing import Dict, Any, List

import yaml

def validate_spec(spec_path: str):
    try:
        with open(spec_path, 'r') as f:
            data = yaml.safe_load(f)
            if not data or not isinstance(data, dict):
                raise ValueError("Spec is empty or not a valid dictionary.")
            if 'openapi' not in data and 'swagger' not in data:
                raise ValueError("Spec is missing 'openapi' or 'swagger' root field.")
            if 'paths' not in data:
                raise ValueError("Spec is missing the required 'paths' field.")
    except Exception as e:
        raise ValueError(f"PARSE_ERROR: Invalid OpenAPI specification {spec_path}: {e}")

def run_oasdiff(base_spec: str, revision_spec: str, command: str = "changelog") -> List[Dict[str, Any]]:
    """
    Run oasdiff to compare two OpenAPI specs.
    command can be "changelog" or "breaking".
    Returns a list of change objects.
    """
    validate_spec(base_spec)
    validate_spec(revision_spec)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    oasdiff_bin = os.path.join(base_dir, "oasdiff.exe")
    oasdiff_bin_linux = os.path.join(base_dir, "oasdiff")
    
    if not os.path.exists(oasdiff_bin):
        if os.path.exists(oasdiff_bin_linux):
            oasdiff_bin = oasdiff_bin_linux
        else:
            oasdiff_bin = "oasdiff"

    cmd = [oasdiff_bin, command, base_spec, revision_spec, "-f", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise ValueError(f"PARSE_ERROR: oasdiff failed to analyze specifications. {result.stderr or result.stdout}")
        
    if result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            raise ValueError(f"PARSE_ERROR: Failed to parse oasdiff JSON output: {result.stdout}")
    return []

def extract_deprecated_endpoints(changes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extract deprecated endpoints from the oasdiff changelog.
    Returns a list of dicts with 'path' and 'method'.
    """
    deprecated = []
    
    for change in changes:
        # Check if the change indicates deprecation or breaking change
        if change.get("id", "").startswith("api-deprecated") or change.get("id", "").startswith("endpoint-removed"):
            path = change.get("path")
            method = change.get("operation")
            
            if path and method:
                deprecated.append({
                    "path": path,
                    "method": method.upper(),
                    "reason": change.get("text", "")
                })
                
    return deprecated
