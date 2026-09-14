import json
from datetime import datetime, timedelta

def generate():
    registry = []
    today = datetime.utcnow().date().isoformat()
    expiry = (datetime.utcnow() + timedelta(days=90)).date().isoformat()

    # 1. STRIPE
    registry.append({
        "sdk_name": "stripe", "sdk_version_range": ">=7.0.0, <10.0.0", "method_path": "stripe.Charge.create", "http_method": "POST", "endpoint_template": "https://api.stripe.com/v1/charges", "source_url": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json", "retrieved_date": today, "source_type": "machine-readable"
    })
    # 2. TWILIO
    registry.append({
        "sdk_name": "twilio", "sdk_version_range": ">=7.0.0", "method_path": "twilio.messages.create", "http_method": "POST", "endpoint_template": "https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json", "source_url": "https://raw.githubusercontent.com/twilio/twilio-oai/main/spec/yaml/twilio_api_v2010.yaml", "retrieved_date": today, "source_type": "machine-readable"
    })
    # 3. OPENAI
    registry.append({
        "sdk_name": "openai", "sdk_version_range": ">=1.0.0", "method_path": "openai.chat.completions.create", "http_method": "POST", "endpoint_template": "https://api.openai.com/v1/chat/completions", "source_url": "https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml", "retrieved_date": today, "source_type": "machine-readable"
    })
    # 4. ANTHROPIC
    registry.append({
        "sdk_name": "anthropic", "sdk_version_range": ">=0.3.0", "method_path": "anthropic.messages.create", "http_method": "POST", "endpoint_template": "https://api.anthropic.com/v1/messages", "source_url": "https://docs.anthropic.com/api/reference/messages-create", "retrieved_date": today, "source_type": "manual", "expiry_date": expiry
    })
    # 5. GITHUB (PyGithub)
    registry.append({
        "sdk_name": "PyGithub", "sdk_version_range": ">=1.50.0", "method_path": "github.Github.get_user", "http_method": "GET", "endpoint_template": "https://api.github.com/users/{username}", "source_url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json", "retrieved_date": today, "source_type": "machine-readable"
    })
    # 6. SLACK
    registry.append({
        "sdk_name": "slack_sdk", "sdk_version_range": ">=3.0.0", "method_path": "client.chat_postMessage", "http_method": "POST", "endpoint_template": "https://slack.com/api/chat.postMessage", "source_url": "https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json", "retrieved_date": today, "source_type": "machine-readable"
    })
    # 7. SENDGRID
    registry.append({
        "sdk_name": "sendgrid", "sdk_version_range": ">=6.0.0", "method_path": "sg.send", "http_method": "POST", "endpoint_template": "https://api.sendgrid.com/v3/mail/send", "source_url": "https://raw.githubusercontent.com/sendgrid/sendgrid-oai/main/oai_v3.yaml", "retrieved_date": today, "source_type": "machine-readable"
    })
    # 8. AWS SDK (BOTO3)
    registry.append({
        "sdk_name": "boto3", "sdk_version_range": ">=1.0.0", "method_path": "s3.put_object", "http_method": "PUT", "endpoint_template": "https://{bucket}.s3.amazonaws.com/{key}", "source_url": "https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/s3/2006-03-01/service-2.json", "retrieved_date": today, "source_type": "machine-readable"
    })

    with open("src/cli/sdk_registry.json", "w") as f:
        json.dump(registry, f, indent=2)
    print("Generated sdk_registry.json with 8 Target SDKs.")

if __name__ == "__main__":
    generate()
