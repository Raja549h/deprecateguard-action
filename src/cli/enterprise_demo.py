import requests
import requests as req
from httpx import get
import aiohttp

def my_func():
    # 1. Standard
    requests.get("https://api.stripe.com/v1/customers")
    
    # 2. Alias
    req.post("https://api.twilio.com/2010-04-01/Accounts")
    
    # 3. Direct import
    get("https://api.github.com/users")
    
    # 4. f-string + privacy leak in query
    cust_id = "cust_9999"
    requests.delete(f"https://api.stripe.com/v1/customers/{cust_id}?secret=sk_test_123456")
    
    # 5. PII in path
    req.put("https://api.example.com/users/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855/update")
