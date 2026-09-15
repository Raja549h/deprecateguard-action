import json
import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript
import os
from typing import List, Dict, Any
from datetime import datetime
from src.cli.ir import HttpCallIR

LANGUAGES = {
    "javascript": tree_sitter.Language(tree_sitter_javascript.language()),
    "typescript": tree_sitter.Language(tree_sitter_typescript.language_typescript()),
}

CALL_TYPES = {"call_expression", "new_expression"}
ARG_DELIMITERS = {"arguments", "template_string"}

def extract_callee(node) -> str:
    if node.type in CALL_TYPES:
        parts = []
        for c in node.children:
            if c.type in ARG_DELIMITERS:
                break
            parts.append(c.text.decode("utf8"))
        return "".join(parts).strip()
    return None

class JSExtractor:
    def __init__(self, lang: str):
        self.lang = lang
        self.parser = tree_sitter.Parser(LANGUAGES[lang])
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        registry_path = os.path.join(base_dir, "sdk_mappings_js.json")
        if os.path.exists(registry_path):
            with open(registry_path, "r") as f:
                registry = json.load(f)
                self.registry_map = {entry["method_path"]: entry for entry in registry}
        else:
            self.registry_map = {}

    def _check_staleness(self, entry: Dict[str, Any]) -> str:
        if entry.get("source_type") == "manual" and "expiry_date" in entry:
            expiry = datetime.fromisoformat(entry["expiry_date"])
            if datetime.utcnow() > expiry:
                return "STALE-COVERAGE"
        return "SDK_MAPPING"

    def scan_code(self, code: bytes, file_path: str) -> List[HttpCallIR]:
        tree = self.parser.parse(code)
        results = []
        
        # Force POSIX paths
        posix_path = file_path.replace("\\", "/")

        def walk(n):
            callee = extract_callee(n)
            if callee:
                # Remove any generic type parameters in TS like method<T>()
                if "<" in callee and ">" in callee:
                    callee = callee.split("<")[0]
                
                if callee in self.registry_map:
                    entry = self.registry_map[callee]
                    resolution_method = self._check_staleness(entry)
                    ir = HttpCallIR(
                        language=self.lang,
                        file=posix_path,
                        line=n.start_point[0] + 1,
                        callee_expression=callee,
                        resolved_endpoint=entry["endpoint_template"],
                        http_method=entry["http_method"],
                        resolution_method=resolution_method
                    )
                    ir.canonical_method = callee
                    results.append(ir)
                else:
                    # direct fetch or request matching for raw http if needed
                    pass
                            
            for c in n.children:
                walk(c)
                
        walk(tree.root_node)
        return results
