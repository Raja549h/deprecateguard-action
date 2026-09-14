import json
import tree_sitter
import tree_sitter_python
from typing import List, Dict, Any
from datetime import datetime
from src.cli.ir import HttpCallIR

LANGUAGES = {
    "py": tree_sitter.Language(tree_sitter_python.language()),
}

CALL_TYPES = {"call", "call_expression", "method_invocation"}
ARG_DELIMITERS = {"argument_list", "arguments", "(", ")", "{"}

def extract_callee(node) -> str:
    if node.type in CALL_TYPES:
        parts = []
        for c in node.children:
            if c.type in ARG_DELIMITERS:
                break
            parts.append(c.text.decode("utf8"))
        return "".join(parts).strip()
    return None

class MultiLanguageExtractor:
    def __init__(self, lang_ext: str):
        self.lang_ext = lang_ext
        self.parser = tree_sitter.Parser(LANGUAGES[lang_ext])
        
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        registry_path = os.path.join(base_dir, "sdk_registry.json")
        with open(registry_path, "r") as f:
            registry = json.load(f)
            self.registry_map = {entry["method_path"]: entry for entry in registry}

    def _check_staleness(self, entry: Dict[str, Any]) -> str:
        if entry.get("source_type") == "manual" and "expiry_date" in entry:
            expiry = datetime.fromisoformat(entry["expiry_date"])
            if datetime.utcnow() > expiry:
                return "STALE-COVERAGE"
        return "SDK_MAPPING"
        
    def build_symbol_table(self, tree) -> dict:
        symbol_table = {}
        def walk(n):
            if n.type == "assignment":
                if len(n.children) >= 3:
                    left = n.children[0].text.decode("utf8")
                    right = n.children[2].text.decode("utf8").lower()
                    if "anthropic" in right:
                        symbol_table[left] = "anthropic"
                    elif "twilio" in right or "client" in right: # naive twilio check
                        # To disambiguate generic Client, we check if twilio is also in the right, but for the MVP:
                        if "twilio" in right or "client" in right and "anthropic" not in right:
                            symbol_table[left] = "twilio"
                    elif "openai" in right:
                        symbol_table[left] = "openai"
            for c in n.children: walk(c)
        walk(tree.root_node)
        return symbol_table

    def scan_code(self, code: bytes, file_path: str) -> List[HttpCallIR]:
        tree = self.parser.parse(code)
        results = []
        
        # Build file-level symbol table to prevent cross-contamination
        symbol_table = self.build_symbol_table(tree)
        
        # Force POSIX paths
        posix_path = file_path.replace("\\", "/")

        def walk(n):
            callee = extract_callee(n)
            if callee:
                parts = callee.split(".")
                base = parts[0]
                
                # Resolve base alias
                resolved_base = symbol_table.get(base, base)
                resolved_callee = f"{resolved_base}.{'.'.join(parts[1:])}" if len(parts) > 1 else resolved_base
                
                if resolved_callee in self.registry_map:
                    entry = self.registry_map[resolved_callee]
                    resolution_method = self._check_staleness(entry)
                    results.append(HttpCallIR(
                        language=self.lang_ext,
                        file=posix_path,
                        line=n.start_point[0] + 1,
                        callee_expression=callee,
                        resolved_endpoint=entry["endpoint_template"],
                        http_method=entry["http_method"],
                        resolution_method=resolution_method
                    ))
                    # Quick hack to inject canonical_method dynamically for SARIF stability
                    results[-1].canonical_method = resolved_callee
                else:
                    # Also try checking if ends with for backward compat for direct matches
                    for method_path, entry in self.registry_map.items():
                        if resolved_callee == method_path or (callee == method_path and base in ["stripe", "github", "sg", "s3"]):
                            resolution_method = self._check_staleness(entry)
                            results.append(HttpCallIR(
                                language=self.lang_ext,
                                file=posix_path,
                                line=n.start_point[0] + 1,
                                callee_expression=callee, # keep original for tracing
                                resolved_endpoint=entry["endpoint_template"],
                                http_method=entry["http_method"],
                                resolution_method=resolution_method
                            ))
                            results[-1].canonical_method = method_path
                            break
                            
            for c in n.children:
                walk(c)
                
        walk(tree.root_node)
        return results

if __name__ == "__main__":
    from dataclasses import asdict
    extractor = MultiLanguageExtractor("py")
    code = b"""from twilio.rest import Client as TwilioClient
from anthropic import Anthropic
twilio_client = TwilioClient("sid", "token")
anthropic_client = Anthropic()
twilio_client.messages.create()
anthropic_client.messages.create()
unknown_client.messages.create()
"""
    calls = extractor.scan_code(code, "fixtures\\test_collision.py")
    for c in calls:
        print(json.dumps(asdict(c)))
