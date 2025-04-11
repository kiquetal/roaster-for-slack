import json
import base64
import os
from lambdas.bot import hello

# Set up environment variables for testing
os.environ['SLACK_OAUTH_TOKEN'] = 'test_token'
os.environ['DYNAMODB_TABLE'] = 'test_table'

# Create a test event with Base64 encoded body
form_data = "token=hAWnnL2YVsIUTQ4Of5CyrnAZ&team_id=T652VH1K3&team_domain=edgedev360&channel_id=C08NGPA9V7S&channel_name=roasterbot&user_id=U65H3UVPV&user_name=kiquetal&command=%2Froast&text=&api_app_id=A08N5R5BXJM&is_enterprise_install=false&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT652VH1K3%2F872855691355%2Fm2i9kYW6TmXbCYM7CF8buJtr&trigger_id=872855694928.209097579649.8a4d63454e0da68bf43f7cda4a255e5f"
encoded_body = base64.b64encode(form_data.encode('utf-8')).decode('utf-8')

test_event = {
    "body": encoded_body,
    "isBase64Encoded": True
}

# Call the hello function with the test event
response = hello(test_event, {})

# Print the response
print("Response:")
print(json.dumps(response, indent=2))

# Check if the user_name is correctly included in the response
response_body = json.loads(response['body'])
if "message" in response_body and "kiquetal" in response_body["message"]:
    print("\nTest PASSED: User name 'kiquetal' is included in the response message.")
else:
    print("\nTest FAILED: User name 'kiquetal' is not included in the response message.")
    print(f"Response message: {response_body.get('message', 'No message found')}")