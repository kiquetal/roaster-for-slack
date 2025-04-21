import base64
import io
import json
import os
import boto3
import datetime

import botocore.exceptions
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_sdk.errors import SlackApiError
from response.wrapper import success_response

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')


def check_and_increment_user_pic_count(user_id):
    """
    Check the user's daily picture generation count and increment it atomically.
    Returns True if the user is allowed to generate a picture, False otherwise.
    """
    today_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE_COUNTER"))

    try:
        # Update the counter atomically
        response = table.update_item(
            Key={'user_id': user_id, 'date': today_date},
            UpdateExpression="SET pic_count = if_not_exists(pic_count, :start) + :inc",
            ExpressionAttributeValues={
                ':start': 0,
                ':inc': 1,
                ':limit': 2
            },
            ConditionExpression="attribute_not_exists(pic_count) OR pic_count < :limit",
            ReturnValues="UPDATED_NEW"
        )
        updated_count = response['Attributes']['pic_count']
        print(f"User {user_id} has generated {updated_count} pictures today.")
        return True  # Allowed to generate a picture
    except botocore.exceptions.ClientError as e:
        print(f"Error updating DynamoDB: {str(e)}")
        return False  # Exceeded daily limit

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

    user_info = client.users_info(user=user_id)
    print("User info response:", user_info)
    sayori_id = user_info["user"]["id"]
    if user_info['ok']:
        user_name = user_info['user']['real_name'] or user_info['user']['name']
    mentioned_user = f"<@{user_id}>"
    # Check and enforce daily limit
    if not check_and_increment_user_pic_count(user_id):
        client.chat_postMessage(
            channel=channel_id,
            text="You have reached your daily limit of 2 pictures. Please try again tomorrow."
        )
        return

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

            "text_prompts": [
                {
                    "text": text,
                    "weight": 1.0 # Optional, but good practice
                }
            ],
        })

        # 2. Invoke the Bedrock Model
        response = bedrock_runtime.invoke_model(
            body=request_body,
            modelId=bedrock_model_id,
            accept = "application/json",
            contentType="application/json"
        )

        # 3. Handle the Response and Send to Slack
        print("response from bedrock")
        print(response)
        response_body = json.loads(response.get("body").read())
        print(response_body['result'])

        base64_image = response_body.get("artifacts")[0].get("base64")
        base64_bytes = base64_image.encode('ascii')
        image_bytes = base64.b64decode(base64_bytes)
        client.files_upload_v2(
            channel=channel_id,
            initial_comment=f"Here's the image I generated for you! Enjoy! {mentioned_user}",
           file=io.BytesIO(image_bytes),

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
