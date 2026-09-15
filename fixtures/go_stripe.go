package main

import (
	"github.com/stripe/stripe-go/v74"
	"github.com/stripe/stripe-go/v74/charge"
)

func createCharge() {
	stripe.Key = "sk_test_123"
	params := &stripe.ChargeParams{
		Amount:   stripe.Int64(2000),
		Currency: stripe.String(string(stripe.CurrencyUSD)),
	}
	ch, _ := charge.New(params)
	_ = ch
}
