import os
from typing import List, Dict, Any
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())

def get_parser(ext: str) -> Parser:
    parser = Parser()
    if ext == ".py":
        parser.language = PY_LANGUAGE
    elif ext in [".js", ".ts"]:
        parser.language = JS_LANGUAGE
    return parser

def find_api_calls_in_file(filepath: str) -> List[Dict[str, Any]]:
    _, ext = os.path.splitext(filepath)
    if ext not in [".py", ".js", ".ts"]:
        return []
        
    parser = get_parser(ext)
    
    with open(filepath, "rb") as f:
        source_code = f.read()
        
    tree = parser.parse(source_code)
    calls = []
    
    # We will do a simple recursive walk of the AST to find `requests.get("...")` or `fetch("...")`
    def walk(node):
        if ext == ".py":
            # Looking for call -> function: attribute(object: identifier(requests), attribute: identifier(get))
            if node.type == "call":
                func_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                if func_node and func_node.type == "attribute" and args_node:
                    obj_node = func_node.child_by_field_name("object")
                    attr_node = func_node.child_by_field_name("attribute")
                    
                    if obj_node and attr_node and obj_node.type == "identifier" and attr_node.type == "identifier":
                        obj_text = obj_node.text.decode("utf8")
                        attr_text = attr_node.text.decode("utf8")
                        
                        if obj_text in ["requests", "client", "session"] and attr_text in ["get", "post", "put", "delete", "patch"]:
                            # Find the first string argument
                            for arg in args_node.children:
                                if arg.type == "string":
                                    # string nodes usually contain string_content
                                    content_node = None
                                    for child in arg.children:
                                        if child.type == "string_content":
                                            content_node = child
                                            break
                                    if content_node:
                                        url = content_node.text.decode("utf8")
                                        calls.append({
                                            "method": attr_text.upper(),
                                            "url": url,
                                            "line": node.start_point[0] + 1
                                        })
                                        break
                                        
        elif ext in [".js", ".ts"]:
            if node.type == "call_expression":
                func_node = node.child_by_field_name("function")
                args_node = node.child_by_field_name("arguments")
                if func_node and func_node.type == "identifier" and args_node:
                    func_text = func_node.text.decode("utf8")
                    if func_text == "fetch":
                        for arg in args_node.children:
                            if arg.type == "string":
                                content_node = None
                                for child in arg.children:
                                    if child.type == "string_fragment":
                                        content_node = child
                                        break
                                if content_node:
                                    url = content_node.text.decode("utf8")
                                    calls.append({
                                        "method": "GET",
                                        "url": url,
                                        "line": node.start_point[0] + 1
                                    })
                                    break
                                    
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return calls
