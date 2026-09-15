SDK_MAPPINGS = {
    # PYTHON
    "stripe.Charge.create": {"method": "POST", "url": "https://api.stripe.com/v1/charges"},
    "stripe.Charge.list": {"method": "GET", "url": "https://api.stripe.com/v1/charges"},
    "stripe.Customer.list": {"method": "GET", "url": "https://api.stripe.com/v1/customers"},
    "stripe.Customer.list_bank_accounts": {"method": "GET", "url": "https://api.stripe.com/v1/customers/{customer}/bank_accounts"},
    
    # JS/TS
    "stripe.charges.create": {"method": "POST", "url": "https://api.stripe.com/v1/charges"},
    "stripe.customers.list": {"method": "GET", "url": "https://api.stripe.com/v1/customers"},
    
    # JAVA
    "Charge.create": {"method": "POST", "url": "https://api.stripe.com/v1/charges"},
    
    # GO
    "charge.New": {"method": "POST", "url": "https://api.stripe.com/v1/charges"},
    
    # RUBY
    "Stripe::Charge.create": {"method": "POST", "url": "https://api.stripe.com/v1/charges"},
}
