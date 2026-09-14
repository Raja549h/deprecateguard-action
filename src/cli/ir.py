from dataclasses import dataclass

@dataclass
class HttpCallIR:
    language: str
    file: str
    line: int
    callee_expression: str
    resolved_endpoint: str
    http_method: str
    resolution_method: str  # 'RAW_HTTP', 'SDK_MAPPING', 'INTERNAL_WRAPPER'
    canonical_method: str = ""
