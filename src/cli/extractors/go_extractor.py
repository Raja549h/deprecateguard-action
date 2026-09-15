import json
import tree_sitter
import tree_sitter_go
import os
from typing import List, Dict, Any
from datetime import datetime
from src.cli.ir import HttpCallIR

LANGUAGES = {
    "go": tree_sitter.Language(tree_sitter_go.language()),
}

CALL_TYPES = {"call_expression"}
ARG_DELIMITERS = {"argument_list"}

def extract_callee(node) -> str:
    if node.type in CALL_TYPES:
        parts = []
        for c in node.children:
            if c.type in ARG_DELIMITERS:
                break
            parts.append(c.text.decode("utf8"))
        return "".join(parts).strip()
    return None

class GoExtractor:
    def __init__(self, lang: str):
        self.lang = lang
        self.parser = tree_sitter.Parser(LANGUAGES[lang])
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        registry_path = os.path.join(base_dir, "sdk_mappings_go.json")
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
        posix_path = file_path.replace(chr(92), "/")

        def walk(n):
            callee = extract_callee(n)
            if callee:
                # Normalize Stripe Go calls: charge.New -> stripe.Charge.New
                parts = callee.split(".")
                if len(parts) == 2 and parts[1] in ["New", "List", "Get", "Update", "Del"]:
                    if parts[0] in ["charge", "customer", "paymentintent", "subscription"]:
                        callee = f"stripe.{parts[0].capitalize()}.{parts[1]}"
                        # Special case for camelCase in Go Stripe SDK
                        if parts[0] == "paymentintent":
                            callee = f"stripe.PaymentIntent.{parts[1]}"
                
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
                            
            for c in n.children:
                walk(c)
                
        walk(tree.root_node)
        return results
