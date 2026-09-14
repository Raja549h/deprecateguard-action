import os
import re
import json
import time
import logging
import requests
from urllib.parse import urlparse
from typing import List, Dict, Any, Set
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    import tree_sitter
    import tree_sitter_python
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

# Enterprise JSON Audit Logging
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "file"):
            log_obj["file"] = record.file
        if hasattr(record, "execution_ms"):
            log_obj["execution_ms"] = record.execution_ms
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
        return json.dumps(log_obj)

logger = logging.getLogger("DeprecateGuard.ASTScanner")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
for h in logger.handlers[:]:
    logger.removeHandler(h)
logger.addHandler(handler)
logger.propagate = False

@dataclass
class HttpCall:
    file_path: str
    line_number: int
    url: str
    method: str

class EnterpriseURLSanitizer:
    @staticmethod
    def sanitize(raw_url: str) -> str:
        try:
            parsed = urlparse(raw_url)
            path = parsed.path
            path = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '{id}', path)
            path = re.sub(r'\b[0-9a-fA-F]{16,}\b', '{id}', path)
            path = re.sub(r'\b\d+\b', '{id}', path)
            scheme = f"{parsed.scheme}://" if parsed.scheme else ""
            netloc = parsed.netloc if parsed.netloc else ""
            if not scheme and not netloc:
                return path
            return f"{scheme}{netloc}{path}"
        except Exception:
            return raw_url

# ----------------- WORKER LOGIC (Runs in isolated processes) -----------------

_worker_state = {}

def init_worker():
    if not HAS_TREE_SITTER:
        raise RuntimeError("Missing tree-sitter packages")
    language = tree_sitter.Language(tree_sitter_python.language())
    parser = tree_sitter.Parser(language)
    _worker_state['language'] = language
    _worker_state['parser'] = parser

def _extract_string_value(args_node) -> str:
    text = ""
    identifier = None
    def walk_args(n):
        nonlocal text, identifier
        if n.type == 'string':
            val = n.text.decode('utf8')
            val = re.sub(r'^[fFbr]*[\'"]{1,3}', '', val)
            val = re.sub(r'[\'"]{1,3}$', '', val)
            text += val
        elif n.type == 'identifier' and not identifier:
            identifier = n.text.decode('utf8')
        for child in n.children:
            walk_args(child)
    walk_args(args_node)
    if not text and identifier:
        return f"{{VAR:{identifier}}}"
    return text

def parse_file_ast(file_path: str):
    with open(file_path, 'rb') as f:
        source_code = f.read()
    return _worker_state['parser'].parse(source_code)

def worker_pass_1(file_path: str) -> Dict[str, Dict[str, str]]:
    """PASS 1: Scan for internal functions that wrap HTTP calls."""
    start_time = time.time()
    if "test" in file_path.lower():
        return {}

    wrappers = {}
    try:
        tree = parse_file_ast(file_path)
        http_clients = {"requests", "httpx", "aiohttp"}
        aliases = {}
        direct_methods = {}
        
        def extract_imports(n):
            if n.type == 'import_statement':
                text = n.text.decode('utf8')
                for client in http_clients:
                    if client in text:
                        if ' as ' in text:
                            alias = text.split(' as ')[-1].strip()
                            aliases[alias] = client
                        else:
                            aliases[client] = client
            elif n.type == 'import_from_statement':
                text = n.text.decode('utf8')
                for client in http_clients:
                    if f"from {client}" in text:
                        for m in ['get', 'post', 'put', 'delete', 'patch']:
                            if m in text: direct_methods[m] = client
            for child in n.children:
                extract_imports(child)
        extract_imports(tree.root_node)

        # Walk to find function definitions and check if they wrap an HTTP call
        def walk_for_wrappers(node):
            if node.type == 'function_definition':
                func_name_node = node.child_by_field_name('name')
                if not func_name_node:
                    return
                func_name = func_name_node.text.decode('utf8')
                
                # Check body for HTTP calls
                body = node.child_by_field_name('body')
                if body:
                    def check_call(n):
                        if n.type == 'call':
                            func = n.child_by_field_name('function')
                            args = n.child_by_field_name('arguments')
                            if func and args:
                                f_text = func.text.decode('utf8')
                                method = None
                                if "." in f_text:
                                    obj, m = f_text.rsplit(".", 1)
                                    if obj in aliases and m in ["get", "post", "put", "delete", "patch"]:
                                        method = m.upper()
                                elif f_text in ["get", "post", "put", "delete", "patch"]:
                                    method = f_text.upper()
                                    
                                if method:
                                    raw_url = _extract_string_value(args)
                                    wrappers[func_name] = {
                                        "method": method,
                                        "url": EnterpriseURLSanitizer.sanitize(raw_url)
                                    }
                        for child in n.children:
                            check_call(child)
                    check_call(body)
            else:
                for child in node.children:
                    walk_for_wrappers(child)
                    
        walk_for_wrappers(tree.root_node)
        
        exec_ms = int((time.time() - start_time) * 1000)
        if wrappers:
            logger.info("ast_pass1_success", extra={"file": file_path, "execution_ms": exec_ms, "extra_data": {"wrappers_found": len(wrappers)}})
    except Exception as e:
        logger.warning(f"ast_pass1_error: {e}", extra={"file": file_path})
    return wrappers

def worker_pass_2(file_path: str, git_root: str, global_wrappers: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """PASS 2: Flag direct HTTP calls AND invocations of internal wrapper functions."""
    start_time = time.time()
    if "test" in file_path.lower():
        return []

    calls = []
    try:
        tree = parse_file_ast(file_path)
        rel_path = os.path.relpath(file_path, git_root)
        
        http_clients = {"requests", "httpx", "aiohttp"}
        aliases = {}
        direct_methods = {}
        
        def extract_imports(n):
            if n.type == 'import_statement':
                text = n.text.decode('utf8')
                for client in http_clients:
                    if client in text:
                        if ' as ' in text:
                            aliases[text.split(' as ')[-1].strip()] = client
                        else:
                            aliases[client] = client
            elif n.type == 'import_from_statement':
                text = n.text.decode('utf8')
                for client in http_clients:
                    if f"from {client}" in text:
                        for m in ['get', 'post', 'put', 'delete', 'patch']:
                            if m in text: direct_methods[m] = client
            for child in n.children:
                extract_imports(child)
        extract_imports(tree.root_node)

        def walk(node):
            if node.type == 'call':
                func = node.child_by_field_name('function')
                args = node.child_by_field_name('arguments')
                if func and args:
                    f_text = func.text.decode('utf8')
                    method = None
                    url = None
                    
                    # Check direct HTTP clients
                    if "." in f_text:
                        obj, m = f_text.rsplit(".", 1)
                        if obj in aliases and m in ["get", "post", "put", "delete", "patch"]:
                            method = m.upper()
                    elif f_text in direct_methods or f_text in ["get", "post", "put", "delete", "patch"]:
                        method = f_text.upper()
                        
                    if method:
                        raw_url = _extract_string_value(args)
                        url = EnterpriseURLSanitizer.sanitize(raw_url)
                    else:
                        # CROSS-FILE TRACING: Check if it's an invocation of a known internal wrapper
                        base_func = f_text.split('.')[-1]
                        if base_func in global_wrappers:
                            wrapper_data = global_wrappers[base_func]
                            method = wrapper_data["method"]
                            url = wrapper_data["url"]
                        else:
                            # SDK CORRELATION LAYER: Map third-party SDK calls to REST endpoints
                            # Import mapping inline to avoid top-level issues in multiprocessing
                            try:
                                from src.cli.sdk_mappings import SDK_MAPPINGS
                            except ImportError:
                                SDK_MAPPINGS = {}
                                
                            # Check for exact matches (e.g. stripe.Charge.create)
                            # or wildcard suffix matches (e.g. client.messages.create)
                            if f_text in SDK_MAPPINGS:
                                sdk_data = SDK_MAPPINGS[f_text]
                                method = sdk_data["method"]
                                url = sdk_data["url"]
                            else:
                                # Loose matching for instance-based SDKs (e.g. self.client.messages.create -> client.messages.create)
                                suffix = ".".join(f_text.split('.')[-3:])
                                if suffix in SDK_MAPPINGS:
                                    sdk_data = SDK_MAPPINGS[suffix]
                                    method = sdk_data["method"]
                                    url = sdk_data["url"]
                            
                    if method and url:
                        calls.append(asdict(HttpCall(
                            file_path=rel_path,
                            line_number=func.start_point[0] + 1,
                            method=method,
                            url=url
                        )))
            for child in node.children:
                walk(child)
        walk(tree.root_node)
        
        exec_ms = int((time.time() - start_time) * 1000)
        logger.info("ast_pass2_success", extra={"file": file_path, "execution_ms": exec_ms, "extra_data": {"calls_extracted": len(calls)}})
    except Exception as e:
        logger.warning(f"ast_pass2_error: {e}", extra={"file": file_path})
    return calls

class HighConcurrencyEnterpriseScanner:
    def __init__(self, git_root: str):
        self.git_root = git_root
        
    def _gather_python_files(self) -> List[str]:
        target_files = []
        for root, dirs, files in os.walk(self.git_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'venv', 'env')]
            for file in files:
                if file.endswith('.py'):
                    target_files.append(os.path.join(root, file))
        return target_files

    def run_two_pass_scan(self) -> List[Dict[str, Any]]:
        target_files = self._gather_python_files()
        logger.info("ast_scan_start", extra={"extra_data": {"total_files": len(target_files)}})
        
        global_wrappers = {}
        # PASS 1: Build Global Symbol Table for Semantic Tracing
        with ProcessPoolExecutor(initializer=init_worker) as executor:
            future_to_file = {executor.submit(worker_pass_1, f): f for f in target_files}
            for future in as_completed(future_to_file):
                try:
                    wrappers = future.result()
                    if wrappers:
                        global_wrappers.update(wrappers)
                except Exception as e:
                    logger.error(f"pass1_process_failed", extra={"extra_data": {"error": str(e)}})

        logger.info("semantic_tracing_built", extra={"extra_data": {"global_wrappers_count": len(global_wrappers)}})

        # PASS 2: Trace Invocations
        all_calls = []
        with ProcessPoolExecutor(initializer=init_worker) as executor:
            future_to_file = {executor.submit(worker_pass_2, f, self.git_root, global_wrappers): f for f in target_files}
            for future in as_completed(future_to_file):
                try:
                    calls = future.result()
                    all_calls.extend(calls)
                except Exception as e:
                    logger.error(f"pass2_process_failed", extra={"extra_data": {"error": str(e)}})
                    
        logger.info("ast_scan_complete", extra={"extra_data": {"total_calls_found": len(all_calls)}})
        return all_calls

    def transmit_payload(self, payload: List[Dict[str, Any]]):
        saas_url = os.getenv("SAAS_BACKEND_URL", "https://api.deprecateguard.com/v1/scan")
        api_key = os.getenv("SAAS_API_KEY", "")
        try:
            resp = requests.post(
                saas_url, 
                json=payload, 
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5.0
            )
            resp.raise_for_status()
            logger.info("saas_transmit_success")
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("saas_transmit_failed", extra={"extra_data": {"error": str(e), "fallback": "FAIL-OPEN"}})
            return []

if __name__ == "__main__":
    scanner = HighConcurrencyEnterpriseScanner(os.getcwd())
    results = scanner.run_two_pass_scan()
    scanner.transmit_payload(results)
