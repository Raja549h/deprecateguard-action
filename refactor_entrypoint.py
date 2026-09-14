import re
with open("src/cli/action_entrypoint.py", "r", encoding="utf-8") as f: code = f.read()
post_func = """
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
"""
code = code.replace("def main():", post_func + "\ndef main():")
old_except = """    except Exception as e:\n        print(f"Error fetching specs: {e}")\n        # Test 7: Fail gracefully, exit 0\n        sys.exit(0)"""
new_except = """    except Exception as e:\n        print(f"Error fetching specs: {e}")\n        fail_comment = "## ⚠️ DeprecateGuard: API Deprecations Detected in PR\\n\\nScan could not complete — spec fetch failed."\n        post_or_update_comment(fail_comment, repo_name, pr_num, token)\n        sys.exit(0)"""
code = code.replace(old_except, new_except)
old_post = """    # 7. Post Comment / Deduplicate (Idempotency)\n    comment_url = ""\n    if comment:\n        comments_url = f"https://api.github.com/repos/{repo_name}/issues/{pr_num}/comments"\n        req = urllib.request.Request(comments_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})\n        existing_comment_id = None\n        try:\n            with urllib.request.urlopen(req) as resp:\n                comments = json.loads(resp.read().decode("utf-8"))\n                for c in comments:\n                    if c["user"]["login"] == "github-actions[bot]" and "?? DeprecateGuard:" in c["body"]:\n                        existing_comment_id = c["id"]\n                        break\n        except Exception:\n            pass\n            \n        if existing_comment_id:\n            # Update existing comment\n            update_url = f"https://api.github.com/repos/{repo_name}/issues/comments/{existing_comment_id}"\n            req = urllib.request.Request(update_url, method="PATCH", data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})\n            try:\n                with urllib.request.urlopen(req) as resp:\n                    resp_data = json.loads(resp.read().decode("utf-8"))\n                    comment_url = resp_data.get("html_url", "")\n                print(f"Updated existing PR comment {existing_comment_id}.")\n            except Exception as e:\n                print("Failed to update comment:", e)\n        else:\n            # Create new comment\n            req = urllib.request.Request(comments_url, data=json.dumps({"body": comment}).encode("utf-8"), headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json"})\n            try:\n                with urllib.request.urlopen(req) as resp:\n                    resp_data = json.loads(resp.read().decode("utf-8"))\n                    comment_url = resp_data.get("html_url", "")\n                print("Posted new PR comment.")\n            except Exception as e:\n                print("Failed to post comment:", e)\n    else:\n        # Check if there is an existing comment we need to remove (since findings dropped to 0)\n        # Actually, standard practice is to leave it or update it to "No findings".\n        pass"""
new_post = """    # 7. Post Comment / Deduplicate (Idempotency)\n    comment_url = post_or_update_comment(comment, repo_name, pr_num, token)"""
code = code.replace(old_post, new_post)
with open("src/cli/action_entrypoint.py", "w", encoding="utf-8") as f: f.write(code)
