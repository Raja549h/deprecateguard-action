package main

import (
	"github.com/twilio/twilio-go"
	openapi "github.com/twilio/twilio-go/rest/api/v2010"
)

func createMessage() {
	client := twilio.NewRestClient()
	params := &openapi.CreateMessageParams{}
	params.SetTo("+1234567890")
	params.SetFrom("+0987654321")
	params.SetBody("Hello")
	
	resp, err := client.Api.CreateMessage(params)
	_ = resp
	_ = err
}
