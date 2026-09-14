import requests
def my_internal_fetcher():
    requests.get("https://api.stripe.com/v1/customers")

def main():
    my_internal_fetcher()
