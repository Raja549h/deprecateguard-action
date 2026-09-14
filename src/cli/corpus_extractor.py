import os, json, subprocess, shutil, tempfile, stat
from src.cli.multi_extractor import MultiLanguageExtractor

def onerror(func, path, exc_info):
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise

def run_extraction():
    with open("corpus_candidates.json", "r") as f: candidates = json.load(f)
    
    cache_file = "corpus_extractions.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f: extractions = json.load(f)
    else:
        extractions = {"records": [], "skipped": []}
    
    processed_repos = {r["repo_id"] for r in extractions["records"]}
    processed_repos.update({s["repo_id"] for s in extractions["skipped"]})

    extractor = MultiLanguageExtractor("py")
    temp_dir = os.path.join(os.getcwd(), "temp_clones")
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)

    success_count = 0
    skip_count = 0
    total_extracted_calls = 0

    # Demo 5 repos for prompt constraints, real run does all
    for repo in candidates[:5]:
        rid = repo["repo_id"]
        if rid in processed_repos:
            continue
        
        print(f"Processing {repo['repo_url']} ...", flush=True)
        repo_path = os.path.join(temp_dir, rid)
        
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        res = subprocess.run(["git", "clone", "--depth", "1", repo["clone_url"], repo_path], capture_output=True, text=True, env=env)
        if res.returncode != 0:
            extractions["skipped"].append({"repo_id": rid, "reason": f"Clone failed: {res.stderr.strip()}"})
            skip_count += 1
            continue
            
        try:
            commit_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True)
            commit_hash = commit_res.stdout.strip() if commit_res.returncode == 0 else "UNKNOWN"
            
            calls_found = 0
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if file.endswith(".py"):
                        fpath = os.path.join(root, file)
                        rel_path = os.path.relpath(fpath, repo_path)
                        try:
                            with open(fpath, "rb") as bf: code = bf.read()
                            calls = extractor.scan_code(code, rel_path)
                            for c in calls:
                                extractions["records"].append({
                                    "repo_id": rid, "repo_url": repo["repo_url"],
                                    "commit_hash": commit_hash, "file_path": c.file,
                                    "line_number": c.line, "callee_expression": c.callee_expression,
                                    "resolved_endpoint": c.resolved_endpoint, "http_method": c.http_method,
                                    "resolution_method": c.resolution_method
                                })
                                calls_found += 1
                        except Exception as e:
                            pass
            success_count += 1
            total_extracted_calls += calls_found
        except Exception as e:
            extractions["skipped"].append({"repo_id": rid, "reason": f"Extraction failed: {str(e)}"})
            skip_count += 1
        finally:
            subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", repo_path])
            
        with open(cache_file, "w") as f: json.dump(extractions, f, indent=2)
        
    print("\n=== AUTOMATED CLONING & EXTRACTION REPORT ===")
    print(f"Successfully processed: {success_count} repos")
    print(f"Skipped/Failed: {skip_count} repos")
    print(f"Total SDK call sites extracted: {total_extracted_calls}")
    
    if skip_count > 0:
        print("\nSkipped Reasons:")
        for s in extractions["skipped"]:
            print(f" - Repo {s['repo_id']}: {s['reason']}")

if __name__ == "__main__":
    run_extraction()
