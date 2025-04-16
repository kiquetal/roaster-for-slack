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

    user_name = "User"
    profile_image_url = None

    try:
        user_info = client.users_info(user=user_id)
        print("User info response:", user_info)
        print("Url profile: ", user_info['user']['profile']['image_72'])
        profile_image_url = user_info['user']['profile'].get('image_original') or user_info['user']['profile'].get('image_72')

    except SlackApiError as e:
        print(f"Error fetching user info: {e.response['error']}")
        return

    # Reply to the Slack channel with the profile picture
    try:
        if channel_id and profile_image_url:
            client.chat_postMessage(
                channel=channel_id,
                blocks=[
                    {
                        "type": "image",
                        "image_url": profile_image_url,
                        "alt_text": f"{user_name}'s profile picture"
                    }
                ]
            )
            print(f"Profile picture sent to channel: {channel_id}")
        elif channel_id and not profile_image_url:
            client.chat_postMessage(
                channel=channel_id,
                text=f"Hey <@{user_id}>, I couldn't find your profile picture."
            )
            print(f"Could not find profile picture for user {user_id} in channel {channel_id}")
    except Exception as e:
        print(f"Error sending message to Slack channel: {e}")
# Lambda handler

app.command("/pic")(ack=fast_handle_message_events,lazy=[handle_message_events])
def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)

# The original hello function is no longer the main handler when using Slack Bolt
# You can remove or comment it out

# def hello(event, context):
#     # ... (original hello function code) ...
#     pass
