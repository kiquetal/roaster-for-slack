import io
import json
import os
import boto3
import datetime
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_sdk.errors import SlackApiError
from response.wrapper import success_response

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')

# Initialize Slack Bolt app
app = App(
    process_before_response=True,
    token=os.environ.get("SLACK_OAUTH_TOKEN")
    , signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)


def fast_handle_message_events(body,ack):
    ack("will return some pic...")

def handle_message_events(respond,body,client):
    print("Receiving command:", body)
    print("after ack")
    user_id = body['user_id']  # Get user ID from command
    channel_id = body['channel_id'] # Get channel ID from command
    text = body['text']  # Get text from command

    if not text:
        client.chat_postMessage(
            channel=channel_id,
            text="Please provide a description for the image you'd like to generate."
        )
        return

    try:
        # 1. Construct the Bedrock Request Body
        bedrock_model_id = "stability.stable-diffusion-xl-v1" # Example model ID
        request_body = json.dumps({
            "steps": 50,
            "width": 512,
            "height": 512,
            "text_prompts": [
                {
                    "text": text,
                    "weight": 1.0 # Optional, but good practice
                }
            ],
            # Add other Stable Diffusion parameters as needed (e.g., cfg_scale, sampler)
        })

        # 2. Invoke the Bedrock Model
        response = bedrock_runtime.invoke_model(
            body=request_body,
            modelId=bedrock_model_id,
            accept="image/png",
            contentType="application/json"
        )

        # 3. Handle the Response and Send to Slack
        response_body = response.get('body').read()
        image_data = io.BytesIO(response_body)
        image_bytes = image_data.getvalue() # Get the content as bytes

        client.files_upload_v2(
            channel=channel_id,
            initial_comment=f"Here's the image I generated for you!",
            files=[
                {
                    "content": image_bytes, # Use the byte value directly
                    "filename": "generated_image.png",
                    "filetype": "png",
                }
            ]
        )
        print(f"Image generated and sent to channel: {channel_id}")

    except Exception as e:
        print(f"Error generating or sending image: {e}")
        client.chat_postMessage(
            channel=channel_id,
            text=f"Sorry, I couldn't generate the image. Error: {e}"
        )
app.command("/pic")(ack=fast_handle_message_events,lazy=[handle_message_events])
def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)

# The original hello function is no longer the main handler when using Slack Bolt
# You can remove or comment it out

# def hello(event, context):
#     # ... (original hello function code) ...
#     pass
