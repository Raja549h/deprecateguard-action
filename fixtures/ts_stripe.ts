import Stripe from 'stripe';
const stripe = new Stripe('sk_test_123');

async function createCharge() {
    const charge = await stripe.charges.create({
        amount: 2000,
        currency: 'usd',
        source: 'tok_visa',
    });
}
