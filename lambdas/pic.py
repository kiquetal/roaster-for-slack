import base64
import io
import json
import os
import random
from base64 import b64decode

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
        model, body = generate_body_for_titan_v2(text)
        # 2. Invoke the Bedrock Model
        response = bedrock_runtime.invoke_model(
            body=body,
            modelId=model,
            accept = "application/json",
            contentType="application/json"
        )

        # 3. Handle the Response and Send to Slack
        print("response from bedrock")
        print(response)
        response_body = json.loads(response.get("body").read())
        model = os.environ.get("MODEL_BEDROCK")
        print(f"The model used is: {model}")
        if model == "stable-diffusion":
            print(response_body['result'])
            base64_image = response_body.get("artifacts")[0].get("base64")
            base64_bytes = base64_image.encode('ascii')
            image_bytes = base64.b64decode(base64_bytes)
        else:
            base64_images = response_body["images"][0]
            image_bytes = b64decode(base64_images)

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

def generate_body_for_stable_diffussion(text):
    try:
        bedrock_model_id = "stability.stable-diffusion-xl-v1" # Example model ID
        request_body = json.dumps({

            "text_prompts": [
                {
                    "text": text,
                    "weight": 1.0 # Optional, but good practice
                }
            ],
        })

        return bedrock_model_id, request_body

    except Exception as e:
        print(f"Error generating body for Stable Diffusion: {e}")
        return None

def generate_body_for_titan_v2(text):
    try:
        # Set the model ID, e.g., Titan Image Generator G1.
        model_id = "amazon.titan-image-generator-v2:0"


        # Generate a random seed.
        seed = random.randint(0, 2147483647)

        # Format the request payload using the model's native structure.
        native_request = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": text},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "cfgScale": 8.0,
                "height": 512,
                "width": 512,
                "seed": seed,
            },
        }

        # Convert the native request to JSON.
        request = json.dumps(native_request)
        return model_id, request
    except Exception as e:
        print(f"Error generating body for Titan V2: {e}")
        return None
