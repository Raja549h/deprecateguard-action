def generate_pr_comment(findings, diff_files=None, repo_full_name="unknown/repo"):
    if diff_files is None: diff_files = set(f["file_path"] for f in findings)
    
    import urllib.parse, hashlib
    repo_hash = hashlib.sha256(repo_full_name.encode('utf-8')).hexdigest()[:8]
    
    hard_findings = []
    soft_findings = []
    
    for f in findings:
        fp = f.get("file_path", f.get("file")).replace("\\", "/")
        if fp not in diff_files:
            continue
        if f.get("finding_type") == "hard":
            hard_findings.append(f)
        else:
            soft_findings.append(f)
            
    if not hard_findings and not soft_findings:
        return None
        
    hard_label = "deprecation" if len(hard_findings) == 1 else "deprecations"
    soft_label = "deprecation" if len(soft_findings) == 1 else "deprecations"
    
    comment = "## ⚠️ DeprecateGuard: API Deprecations Detected in PR\n\n"
    comment += f"**Findings:** {len(hard_findings)} hard, {len(soft_findings)} soft\n\n"
    comment += "---\n\n"
    comment += "The following third-party SDK calls in your diff resolve to endpoints that are currently deprecated by the provider.\n\n"
    
    def render_finding(f, prefix="DG-"):
        fp = f.get("file_path", f.get("file")).replace("\\", "/")
        ln = f.get("line_number", f.get("line"))
        ce = f.get("callee_expression", "unknown")
        ep = f.get("resolved_endpoint", "unknown")
        sv = f.get("spec_version", "UNKNOWN")
        
        block = f"### `{fp}:{ln}`\n"
        block += f"- **SDK Method:** `{ce}`\n"
        block += f"- **Resolves To:** `{ep}`\n"
        block += f"- **Spec Version:** `{sv}`\n"
        
        if f.get("finding_type") == "soft":
            block += f"- **Soft Deprecation:** indicated in the provider's documentation, not in the OpenAPI deprecated flag.\n"
            block += f"  - **Phrase Match:** `{f.get('soft_phrase', '')}`\n"
            block += f"  - **Context:** \"{f.get('soft_sentence', '')}\"\n"
            block += f"- **Spec URL:** {f.get('spec_url', 'UNKNOWN')} (Retrieved: {f.get('spec_date', 'UNKNOWN')})\n\n"
            
        canon = f.get("canonical_method", ce).upper().replace(".", "-")
        finding_id = f"{prefix}{canon}"
        
        telemetry_base = "https://github.com/Raja549h/deprecateguard-telemetry/issues/new"
        confirm_body = f"Voting confirm for {finding_id} at {fp}:{ln}\n\nRepoHash: {repo_hash}"
        fp_body = f"Voting false positive for {finding_id} at {fp}:{ln}\n\nRepoHash: {repo_hash}"
        confirm_url = f"{telemetry_base}?title=VOTE-confirm-{finding_id}&body={urllib.parse.quote(confirm_body)}"
        fp_url = f"{telemetry_base}?title=VOTE-false_positive-{finding_id}&body={urllib.parse.quote(fp_body)}"
        
        block += f"[✅ Confirm]({confirm_url}) | [❌ False Positive]({fp_url})\n\n"
        return block
        
    if hard_findings:
        comment += "### Hard deprecations (spec-confirmed)\n\n"
        for f in hard_findings:
            comment += render_finding(f, prefix="DG-")
            
    if soft_findings:
        comment += "### Soft deprecations (documentation-indicated)\n\n"
        for f in soft_findings:
            comment += render_finding(f, prefix="DG-SOFT-")
            
    with open("pr_comment.md", "w", encoding="utf-8") as out:
        out.write(comment)
    return comment
