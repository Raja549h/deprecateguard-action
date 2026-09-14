import os, logging, requests
from github_checks import GitHubCheckRunIntegration
logging.basicConfig(level=logging.INFO)
os.environ["GITHUB_TOKEN"] = os.environ.get("GITHUB_TOKEN", "")
os.environ["GITHUB_REPOSITORY"] = "Raja549h/project"
os.environ["GITHUB_SHA"] = "main"
try:
    integration = GitHubCheckRunIntegration()
    integration.publish_check([{"file_path": "a", "line_number": 1, "severity": "HIGH", "reason": "a"}])
except requests.exceptions.RequestException as e:
    if hasattr(e, "response") and e.response:
        print("BODY:", e.response.text)
