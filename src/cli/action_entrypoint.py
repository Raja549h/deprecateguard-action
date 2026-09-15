import os, json, urllib.request, urllib.parse, sys
from multi_extractor import MultiLanguageExtractor
from pr_commenter import generate_pr_comment
from sarif_emitter import generate_sarif
from dataclasses import asdict


def post_or_update_comment(comment, repo_name, pr_num, token):
    if not comment: return ""
    import urllib.request, json
    comments_url = f"https://api.github.com/repos/{repo_name}/issues/{pr_num}/comments"
    req = urllib.request.Request(comments_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})
    existing_id = None
    try:
        with urllib.request.urlopen(req) as resp:
            for c in json.loads(resp.read().decode("utf-8")):
                if c["user"]["login"] == "github-actions[bot]" and "DeprecateGuard:" in c["body"]:
                    existing_id = c["id"]
                    break
    except: pass
    try:
        if existing_id:
            req = urllib.request.Request(f"https://api.github.com/repos/{repo_name}/issues/comments/{existing_id}", method="PATCH", data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
        else:
            req = urllib.request.Request(comments_url, method="POST", data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8")).get("html_url", "")
    except Exception as e: print("Post failed:", e)
    return ""

def main():
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    repo_name = os.environ.get("GITHUB_REPOSITORY", "unknown/repo")
    token = os.environ.get("GITHUB_TOKEN")
    
    if not event_path or not os.path.exists(event_path):
        print("No GITHUB_EVENT_PATH, exiting.")
        return
        
    with open(event_path, "r") as f:
        event_data = json.load(f)
        
    mode = os.environ.get("INPUT_MODE", "pr-comment")
    pr_num = None
    diff_files = None
    if mode == "pr-comment":
        if "pull_request" not in event_data:
            print("PR-comment mode: no pull request context, exiting. Use mode: scheduled-audit for whole-repo scans.")
            return
        pr_num = event_data["pull_request"]["number"]
        # 1. Diff Scoping: fetch PR diff
        diff_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_num}/files"
        req = urllib.request.Request(diff_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})
        try:
            with urllib.request.urlopen(req) as resp:
                files_data = json.loads(resp.read().decode("utf-8"))
                diff_files = set(f["filename"] for f in files_data if f["status"] != "removed")
        except Exception as e:
            print("Failed to get PR files:", e)
            diff_files = None # Fallback to all files
    elif mode == "scheduled-audit":
        pass # diff_files remains None (whole repo)
        
    # 2. Extract calls
    extractor = MultiLanguageExtractor("py")
    extracted = []
    for root, dirs, files in os.walk(workspace):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, workspace).replace("\\", "/")
                # Skip if not in diff (Diff scoping performance optimization)
                if diff_files is not None and rel_path not in diff_files:
                    continue
                try:
                    with open(path, "rb") as f: code = f.read()
                    calls = extractor.scan_code(code, rel_path)
                    for c in calls:
                        d = asdict(c)
                        d["file_path"] = d["file"]
                        d["line_number"] = d["line"]
                        # We only care about calls that matched the registry
                        if d.get("resolved_endpoint"):
                            d["ground_truth"] = "GROUND_TRUTH_POSITIVE"
                            d["ground_truth_confidence"] = "DETERMINISTIC"
                            extracted.append(d)
                except Exception:
                    pass

    # 3. Label against real OpenAPI specs
    import spec_analyzer
    deprecated_findings = []
    for c in extracted:
        canon = c.get("canonical_method", "")
        provider = canon.split(".")[0].lower() if canon else ""
        endpoint_url = c.get("resolved_endpoint", "")
        http_method = c.get("resolved_method", "POST")
        analysis = spec_analyzer.analyze_endpoint(provider, endpoint_url, http_method)
        if analysis:
            if analysis["status"] == "spec_unavailable":
                fail_comment = f"## ⚠️ DeprecateGuard: Scan could not complete — spec fetch failed for provider {analysis.get('provider', 'UNKNOWN')}. No findings reported."
                post_or_update_comment(fail_comment, repo_name, pr_num, token)
                sys.exit(0)
            elif analysis["status"] == "deprecated":
                c["finding_type"] = analysis["type"]
                c["ground_truth_confidence"] = analysis["confidence"]
                c["sarif_level"] = analysis["sarif_level"]
                c["spec_date"] = analysis["date"]
                c["spec_url"] = analysis["url"]
                c["spec_version"] = analysis.get("spec_version", "UNKNOWN")
                if analysis["type"] == "soft":
                    c["soft_phrase"] = analysis["phrase"]
                    c["soft_sentence"] = analysis["sentence"]
                deprecated_findings.append(c)
    
    # 5. Emit SARIF
    generate_sarif(deprecated_findings, "deprecateguard_results.sarif")
    
    output_count = len(deprecated_findings)
    hard_count = sum(1 for f in deprecated_findings if f.get("finding_type") == "hard")
    soft_count = sum(1 for f in deprecated_findings if f.get("finding_type") == "soft")
    
    comment_url = ""
    audit_issue_url = ""

    if mode == "pr-comment":
        # 6. Generate PR Markdown Comment
        comment = generate_pr_comment(deprecated_findings, diff_files=diff_files, repo_full_name=repo_name)
        if comment:
            comments_url = f"https://api.github.com/repos/{repo_name}/issues/{pr_num}/comments"
            req = urllib.request.Request(comments_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})
            existing_comment_id = None
            try:
                with urllib.request.urlopen(req) as resp:
                    comments = json.loads(resp.read().decode("utf-8"))
                    for c in comments:
                        if c["user"]["login"] == "github-actions[bot]" and "DeprecateGuard:" in c["body"]:
                            existing_comment_id = c["id"]
                            break
            except Exception:
                pass
                
            if existing_comment_id:
                update_url = f"https://api.github.com/repos/{repo_name}/issues/comments/{existing_comment_id}"
                req = urllib.request.Request(update_url, method="PATCH", data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(req) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        comment_url = resp_data.get("html_url", "")
                    print(f"Updated existing PR comment {existing_comment_id}.")
                except Exception as e:
                    print("Failed to update comment:", e)
            else:
                req = urllib.request.Request(comments_url, data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(req) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        comment_url = resp_data.get("html_url", "")
                    print("Posted new PR comment.")
                except Exception as e:
                    print("Failed to post comment:", e)
    elif mode == "scheduled-audit":
        audit_issue_url = post_or_update_audit_issue(repo_name, deprecated_findings, token, os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/" + repo_name + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", ""))
                
    # 8. Set Outputs
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"findings_count={output_count}\n")
            f.write(f"hard_findings_count={hard_count}\n")
            f.write(f"soft_findings_count={soft_count}\n")
            f.write(f"sarif_path=deprecateguard_results.sarif\n")
            f.write(f"comment_url={comment_url}\n")
            f.write(f"audit_issue_url={audit_issue_url}\n")
            
def post_or_update_comment(comment, repo_name, pr_num, token):
    import urllib.request, json
    comments_url = f"https://api.github.com/repos/{repo_name}/issues/{pr_num}/comments"
    req = urllib.request.Request(comments_url, data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp: pass
    except Exception: pass
    return ""



def post_or_update_audit_issue(repo_name, findings, token, run_url):
    import urllib.request, json, os, datetime
    from pr_commenter import generate_pr_comment
    findings_body = generate_pr_comment(findings, repo_full_name=repo_name) or "No deprecated endpoints found."
    
    if "## ⚠️ DeprecateGuard: API Deprecations Detected in PR" in findings_body:
        findings_body = findings_body.replace("## ⚠️ DeprecateGuard: API Deprecations Detected in PR\n\n", "")
    findings_body = findings_body.replace("in your diff", "in your repository")
    
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    trigger = os.environ.get("GITHUB_EVENT_NAME", "manual")
    if trigger == "schedule":
        trigger = "schedule"
    else:
        trigger = "manual"
        
    hard_count = sum(1 for f in findings if f.get("finding_type") == "hard")
    soft_count = sum(1 for f in findings if f.get("finding_type") == "soft")
    
    body = f"## ⚠️ DeprecateGuard: Scheduled Audit Report\n\n"
    body += f"**Last Scan Timestamp:** {timestamp}\n"
    body += f"**Scan Trigger:** {trigger}\n"
    body += f"**Commit SHA:** `{os.environ.get('GITHUB_SHA', 'unknown')}`\n"
    body += f"**Run Logs:** [View Run]({run_url})\n\n"
    body += findings_body
    
    title = "DeprecateGuard: Scheduled Audit Report"
    
    search_url = f"https://api.github.com/repos/{repo_name}/issues?state=all&creator=app/github-actions"
    req = urllib.request.Request(search_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})
    existing_issue_number = None
    try:
        with urllib.request.urlopen(req) as resp:
            issues = json.loads(resp.read().decode("utf-8"))
            for issue in issues:
                if issue["title"] == title and "pull_request" not in issue:
                    existing_issue_number = issue["number"]
                    break
    except Exception as e:
        print("Failed to search issues:", e)
        
    if existing_issue_number:
        url = f"https://api.github.com/repos/{repo_name}/issues/{existing_issue_number}"
        req = urllib.request.Request(url, method="PATCH", data=json.dumps({"body": body, "state": "open"}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"Updated existing audit issue #{existing_issue_number}")
                return data.get("html_url", "")
        except Exception as e:
            print("Failed to update issue:", e)
            return ""
    else:
        url = f"https://api.github.com/repos/{repo_name}/issues"
        req = urllib.request.Request(url, method="POST", data=json.dumps({"title": title, "body": body}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                print("Created new audit issue.")
                return data.get("html_url", "")
        except Exception as e:
            print("Failed to create issue:", e)
            return ""


if __name__ == "__main__": main()
