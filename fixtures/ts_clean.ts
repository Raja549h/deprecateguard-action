import Stripe from 'stripe';
const stripe = new Stripe('sk_test_123');

async function createPaymentIntent() {
    const pi = await stripe.paymentIntents.create({
        amount: 2000,
        currency: 'usd',
    });
}
