package main

import (
	"github.com/stripe/stripe-go/v74"
	"github.com/stripe/stripe-go/v74/paymentintent"
)

func createPaymentIntent() {
	stripe.Key = "sk_test_123"
	params := &stripe.PaymentIntentParams{
		Amount:   stripe.Int64(2000),
		Currency: stripe.String(string(stripe.CurrencyUSD)),
	}
	pi, _ := paymentintent.New(params)
	_ = pi
}
