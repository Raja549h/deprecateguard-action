import re, sys
from src.cli.real_spec_fetcher_fast import get_real_spec_version
def test_version_format(v):
    if not re.match(r"^[-_.a-zA-Z0-9]+$", v):
        print(f"FAIL: invalid characters in version: {v}")
        sys.exit(1)
v = get_real_spec_version("https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json")
test_version_format(v)
print("PASS")
