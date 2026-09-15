import { Twilio } from "twilio";
const client = new Twilio("accountSid", "authToken");

async function sendMessage() {
    const message = await client.messages.create({
        body: "Hello from Twilio",
        from: "+12345678901",
        to: "+12345678902"
    });
}
