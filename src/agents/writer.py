import os
import json
import requests
from typing import List, Dict, Any

class WriterAgent:
    """
    LLM-based agent that formats the deterministic detection output into 
    human-readable, schema-constrained migration notices.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
        
    def generate_notice(self, impact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes a single impacted call-site and generates a JSON migration notice.
        """
        # The prompt strictly instructs the LLM to only format the data, 
        # not to make any determinations about deprecation itself.
        prompt = f"""
        You are a technical writer API. Your job is to generate a JSON migration notice for a developer.
        
        Deterministic Detection Engine found the following deprecated API usage:
        - File: {impact_data.get('file')}
        - Line: {impact_data.get('line')}
        - Method: {impact_data.get('method')}
        - URL: {impact_data.get('url')}
        - Reason: {impact_data.get('reason')}
        
        Generate a strict JSON object with the following schema:
        {{
            "title": "string (A short, urgent title)",
            "message": "string (A clear explanation of what is deprecated and where)",
            "action_required": "string (What the developer needs to do)",
            "severity": "string (HIGH, MEDIUM, LOW)"
        }}
        
        Return ONLY valid JSON. No markdown formatting or extra text.
        """
        
        if not self.api_key:
            # Fallback mock for local testing without API key
            return {
                "title": f"Deprecated API Call in {os.path.basename(impact_data.get('file', ''))}",
                "message": f"You are calling a deprecated API ({impact_data.get('method')} {impact_data.get('url')}) at line {impact_data.get('line')}. Reason: {impact_data.get('reason')}",
                "action_required": "Please update this call to use the latest API version.",
                "severity": "HIGH",
                "_mocked": True
            }
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistral-large-latest", # or open-mixtral
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            print(f"Failed to generate notice via LLM: {e}")
            # Fallback on failure
            return {
                "title": "Deprecation Notice",
                "message": f"Deprecated call found in {impact_data.get('file')} at line {impact_data.get('line')}",
                "action_required": "Review API documentation.",
                "severity": "HIGH",
                "error": str(e)
            }
