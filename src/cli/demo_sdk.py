import stripe
from twilio.rest import Client

def do_payment():
    stripe.Charge.create(
        amount=2000,
        currency="usd"
    )

def send_sms():
    client = Client("abc", "def")
    client.messages.create(
        body="Hello",
        from_="+1234567890",
        to="+0987654321"
    )
