import os
import json
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger("DeprecateGuard.GitHubChecks")

class GitHubCheckRunIntegration:
    """
    Handles seamless integration with GitHub's Checks API to annotate 
    deprecated API calls directly on the offending lines in a Pull Request.
    """
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY") # format: owner/repo
        
        # Correctly resolve the PR HEAD SHA (GITHUB_SHA is a merge commit in PRs)
        self.sha = os.getenv("GITHUB_SHA")
        event_path = os.getenv("GITHUB_EVENT_PATH")
        event_name = os.getenv("GITHUB_EVENT_NAME")
        
        if event_name == "pull_request" and event_path and os.path.exists(event_path):
            try:
                with open(event_path, "r") as f:
                    event_data = json.load(f)
                    self.sha = event_data.get("pull_request", {}).get("head", {}).get("sha", self.sha)
            except Exception as e:
                logger.warning(f"Failed to read PR head SHA, falling back to GITHUB_SHA: {e}")
        
        if not all([self.github_token, self.repo, self.sha]):
            logger.error("Missing required GitHub environment variables.")
            raise ValueError("Environment misconfigured for GitHub Checks.")

        self.api_base = f"https://api.github.com/repos/{self.repo}/check-runs"
        self.headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def _format_annotations(self, deprecations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts SaaS deprecation responses into GitHub annotation objects."""
        annotations = []
        for dep in deprecations:
            # Ensure path is always forward-slashed for GitHub relative pathing
            path = dep.get("file_path", "").replace("\\", "/")
            annotations.append({
                "path": path,
                "start_line": dep.get("line_number"),
                "end_line": dep.get("line_number"),
                "annotation_level": "failure" if dep.get("severity") == "HIGH" else "warning",
                "message": f"🚨 DEPRECATED API: {dep.get('reason')}",
                "title": "DeprecateGuard Alert"
            })
        return annotations

    def publish_check(self, deprecations: List[Dict[str, Any]]) -> None:
        """Creates a Check Run on the commit with inline code annotations using pagination."""
        if not deprecations:
            logger.info("No deprecations found. Publishing success check.")
            conclusion = "success"
            summary = "All clear! No deprecated API usage detected."
            annotations = []
        else:
            logger.warning(f"Publishing {len(deprecations)} deprecation warnings.")
            conclusion = "action_required"
            summary = f"Detected {len(deprecations)} deprecated API calls in this branch."
            annotations = self._format_annotations(deprecations)

        # Chunk annotations into groups of 50 (GitHub API limit)
        chunks = [annotations[i:i+50] for i in range(0, len(annotations), 50)]
        
        payload = {
            "name": "DeprecateGuard Scanner",
            "head_sha": self.sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": "API Deprecation Impact Report",
                "summary": summary,
                "annotations": chunks[0] if chunks else []
            }
        }

        try:
            # POST the first chunk to create the check run
            response = requests.post(self.api_base, headers=self.headers, json=payload)
            response.raise_for_status()
            check_run_id = response.json().get("id")
            logger.info(f"Successfully published GitHub Check Run: {response.json().get('html_url')}")
            
            # PATCH the remaining chunks to the same check_run_id
            for i, chunk in enumerate(chunks[1:], start=1):
                patch_payload = {
                    "output": {
                        "title": "API Deprecation Impact Report",
                        "summary": summary,
                        "annotations": chunk
                    }
                }
                patch_resp = requests.patch(f"{self.api_base}/{check_run_id}", headers=self.headers, json=patch_payload)
                patch_resp.raise_for_status()
                logger.info(f"Published annotation chunk {i+1}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to publish GitHub Check Run: {e.response.text if hasattr(e, 'response') and e.response else e}")
            raise
