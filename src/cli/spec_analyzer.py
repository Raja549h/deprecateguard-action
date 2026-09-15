import urllib.request, json, re, datetime, os, time
from urllib.parse import urlparse, unquote
SPEC_URLS = {
    "stripe": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
    "twilio": "https://raw.githubusercontent.com/twilio/twilio-oas/main/spec/yaml/twilio_api_v2010.yaml",
    "github": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
    "anthropic": "https://raw.githubusercontent.com/anthropics/anthropic-openapi/main/openapi.yaml"
}
_cache = {}
CACHE_DIR = "/tmp/deprecateguard-specs"
def get_spec(provider):
    if provider in _cache: return _cache[provider]
    url = SPEC_URLS.get(provider)
    if not url: return None, None, None
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{provider}.json")
    if os.path.exists(cache_file):
        if time.time() - os.path.getmtime(cache_file) < 86400:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    data = cached_data.get("data")
                    fetch_date = cached_data.get("fetch_date")
                    _cache[provider] = (data, fetch_date, url)
                    return _cache[provider]
            except Exception:
                pass
    req = urllib.request.Request(url, headers={"User-Agent": "DeprecateGuard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            if url.endswith(".yaml") or url.endswith(".yml"):
                try:
                    import yaml
                    data = yaml.safe_load(content)
                except ImportError:
                    data = {}
            else:
                data = json.loads(content)
            fetch_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"fetch_date": fetch_date, "data": data}, f)
            except Exception:
                pass
            _cache[provider] = (data, fetch_date, url)
            return _cache[provider]
    except Exception as e: print(e); return None, None, None
def analyze_endpoint(provider, endpoint_url, http_method):
    spec_data, fetch_date, spec_url = get_spec(provider)
    if not spec_data: 
        return {"status": "spec_unavailable", "provider": provider}
    
    spec_version = spec_data.get("info", {}).get("version", "UNKNOWN")
    path = unquote(urlparse(endpoint_url).path)
    op = spec_data.get("paths", {}).get(path, {}).get(http_method.lower())
    
    if not op: 
        return {"status": "clean", "spec_version": spec_version}
    
    # Layer 1
    if op.get("deprecated") is True:
        return {"status": "deprecated", "type": "hard", "confidence": "DETERMINISTIC", "sarif_level": "warning", "date": fetch_date, "url": spec_url, "spec_version": spec_version}
        
    # Layer 2
    desc = op.get("description", "")
    phrases = ["no longer recommended", "has been deprecated", "is deprecated", "deprecated in favor of", "will be sunset"]
    
    for p in phrases:
        if re.search(r"\b" + re.escape(p) + r"\b", desc, re.IGNORECASE):
            clean_desc = re.sub(r"<[^>]+>", "", desc).replace("\n", " ")
            sentences = re.split(r"(?<=[.!?]) +", clean_desc)
            match_sentence = next((s for s in sentences if re.search(r"\b" + re.escape(p) + r"\b", s, re.IGNORECASE)), clean_desc)
            if len(match_sentence) > 200: match_sentence = match_sentence[:197] + "..."
            return {"status": "deprecated", "type": "soft", "confidence": "SOFT_DEPRECATION", "sarif_level": "note", "phrase": p, "sentence": match_sentence, "date": fetch_date, "url": spec_url, "spec_version": spec_version}
            
    return {"status": "clean", "spec_version": spec_version}
