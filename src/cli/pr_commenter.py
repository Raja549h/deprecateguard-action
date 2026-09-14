def generate_pr_comment(findings, diff_files=None, repo_full_name="unknown/repo"):
    if diff_files is None: diff_files = set(f["file_path"] for f in findings)
    
    comment = "## ⚠️ DeprecateGuard: API Deprecations Detected in PR\n\n"
    comment += "The following third-party SDK calls in your diff resolve to endpoints that are currently deprecated by the provider.\n\n"
    
    count = 0
    for f in findings:
        fp = f["file_path"].replace("\\", "/")
        if fp not in diff_files:
            continue
        
        count += 1
        ln = f["line_number"]
        ce = f.get("callee_expression", "unknown")
        ep = f.get("resolved_endpoint", "unknown")
        
        comment += f"### `{fp}:{ln}`\n"
        comment += f"- **SDK Method:** `{ce}`\n"
        comment += f"- **Resolves To:** `{ep}`\n"
        sv = f.get("spec_version", "UNKNOWN")
        comment += f"- **Spec Version:** `{sv}`\n"
        conf = f.get("ground_truth_confidence", "HEURISTIC")
        comment += f"- **Confidence:** {conf}\n\n"
        # Feedback telemetry buttons via GitHub Issues
        telemetry_base = "https://github.com/Raja549h/deprecateguard-telemetry/issues/new"
        id_str = f"{fp}-{ln}-{ce}".replace(" ", "_")
        
        canon = f.get("canonical_method", ce).upper().replace(".", "-")
        finding_id = f"DG-{canon}"
        
        # Derive a stable repo_hash
        import hashlib
        repo_hash = hashlib.sha256(repo_full_name.encode('utf-8')).hexdigest()[:8]
        
        confirm_body = f"Voting confirm for {finding_id} at {fp}:{ln}\n\nRepoHash: {repo_hash}"
        fp_body = f"Voting false positive for {finding_id} at {fp}:{ln}\n\nRepoHash: {repo_hash}"
        
        import urllib.parse
        confirm_url = f"{telemetry_base}?title=VOTE-confirm-{finding_id}&body={urllib.parse.quote(confirm_body)}"
        fp_url = f"{telemetry_base}?title=VOTE-false_positive-{finding_id}&body={urllib.parse.quote(fp_body)}"
        
        comment += f"[✅ Confirm]({confirm_url}) | [❌ False Positive]({fp_url})\n\n"
        
    if count == 0:
        return None # No comment needed
        
    with open("pr_comment.md", "w", encoding="utf-8") as out:
        out.write(comment)
    return comment
