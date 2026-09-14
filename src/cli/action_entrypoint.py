import os, json, urllib.request, urllib.parse
from multi_extractor import MultiLanguageExtractor
from pr_commenter import generate_pr_comment
from dataclasses import asdict

def main():
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    extractor = MultiLanguageExtractor("py")
    records = []
    
    for root, dirs, files in os.walk(workspace):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "rb") as f: code = f.read()
                rel_path = os.path.relpath(path, workspace)
                calls = extractor.scan_code(code, rel_path)
                for c in calls:
                    d = asdict(c)
                    d["file_path"] = d["file"]
                    d["line_number"] = d["line"]
                    d["ground_truth_confidence"] = "DETERMINISTIC"
                    records.append(d)
    
    comment = generate_pr_comment(records)
    if not comment: print("No findings."); return
    
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path): return
    
    with open(event_path, "r") as f: event_data = json.load(f)
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    
    if "pull_request" in event_data:
        pr_num = event_data["pull_request"]["number"]
        url = f"https://api.github.com/repos/{repo_name}/issues/{pr_num}/comments"
    else:
        print("Not a PR, skipping comment.")
        return
    
    req = urllib.request.Request(url, data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    urllib.request.urlopen(req)
    print("Posted comment.")

if __name__ == "__main__": main()
