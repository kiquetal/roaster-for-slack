import json
import os
import boto3
import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from response.wrapper import success_response

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')

def create_roast_prompt(user_name, user_attributes):
    """
    Create a prompt for Bedrock to generate a roast based on user attributes.

    Args:
        user_name (str): The user's name
        user_attributes (dict): User attributes from DynamoDB

    Returns:
        str: A prompt for Bedrock
    """
    # Extract attributes for the roast
    attributes_text = ""
    if user_attributes:
        for key, value in user_attributes.items():
            attributes_text += f"- {key}: {value}\n"
    else:
        attributes_text = "- No specific attributes available\n"

    # Create the prompt
    prompt = f"""
    You are a witty roast comedian. Create a funny, light-hearted roast for a person named {user_name} 
    based on the following attributes:

    {attributes_text}

    The roast should be humorous but not mean-spirited or offensive. Keep it under 30 words.
    Add emoji at the end of the roast to make it more fun.
    """

    return prompt

def generate_roast(prompt):
    """
    Generate a roast using Amazon Bedrock.

    Args:
        prompt (str): The prompt for Bedrock

    Returns:
        str: The generated roast
    """
    try:
        # Use Claude model for roast generation
        model_id = "anthropic.claude-v2"

        # Prepare the request body
        request_body = {
            "prompt": prompt,
            "max_tokens_to_sample": 300,
            "temperature": 0.8,
            "top_p": 0.9,
        }

        # Call Bedrock to generate the roast
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )

        # Parse the response
        response_body = json.loads(response['body'].read())
        roast = response_body.get('completion', '')

        return roast.strip()
    except Exception as e:
        print(f"Error generating roast with Bedrock: {e}")
        return None


def hello(event, context):
    # Extract user information from the event
    user_id = None
    user_name = "User"

    # Parse the event body if it exists
    if event.get('body'):
        try:
            body_json = json.loads(event['body'])
            # Extract user_id from Slack event
            if 'event' in body_json and 'user' in body_json['event']:
                user_id = body_json['event']['user']
            elif 'user_id' in body_json:
                user_id = body_json['user_id']
        except (json.JSONDecodeError, KeyError):
            pass

    # If we have a user_id, try to get the user's real name using Slack API
    slack_profile = {}
    if user_id:
        # Get OAuth token from environment variable
        slack_token = os.environ.get('SLACK_OAUTH_TOKEN')
        if slack_token:
            try:
                client = WebClient(token=slack_token)
                user_info = client.users_info(user=user_id)
                if user_info['ok']:
                    user_name = user_info['user']['real_name'] or user_info['user']['name']

                    # Extract profile attributes from Slack
                    if 'user' in user_info and 'profile' in user_info['user']:
                        profile = user_info['user']['profile']
                        slack_profile = {
                            'display_name': profile.get('display_name', ''),
                            'status_text': profile.get('status_text', ''),
                            'status_emoji': profile.get('status_emoji', ''),
                            'title': profile.get('title', ''),
                            'phone': profile.get('phone', ''),
                            'email': profile.get('email', ''),
                            'image_original': profile.get('image_original', ''),
                            'image_72': profile.get('image_72', '')
                        }
            except SlackApiError as e:
                print(f"Error fetching user info: {e}")

    # Get user attributes from DynamoDB
    user_attributes = {}
    try:
        # Get the DynamoDB table name from environment or construct it
        table_name = os.environ.get('DYNAMODB_TABLE', 'roaster-for-slack-conversation-context')
        table = dynamodb.Table(table_name)

        # Create a sort key with the user's name
        sk = f"#USER#{user_name}"

        # Store user profile in DynamoDB
        if user_id:
            # First, try to get existing attributes
            try:
                response = table.get_item(
                    Key={
                        'user_id': user_id,
                        'sk': sk
                    }
                )

                if 'Item' in response:
                    user_attributes = response['Item'].get('attributes', {})
            except Exception as e:
                print(f"Error fetching user attributes from DynamoDB: {e}")

            # Update or create the user profile in DynamoDB
            try:
                table.put_item(
                    Item={
                        'user_id': user_id,
                        'sk': sk,
                        'attributes': slack_profile,
                        'updated_at': str(datetime.datetime.now())
                    }
                )
            except Exception as e:
                print(f"Error storing user profile in DynamoDB: {e}")
    except Exception as e:
        print(f"Error with DynamoDB operations: {e}")

    # Create a prompt for Bedrock
    #prompt = create_roast_prompt(user_name, user_attributes)

    # Call Bedrock to generate a roast
    #roast = generate_roast(prompt)

    # Print the incoming data from Slack for debugging
    print(f"Incoming event data: {json.dumps(event, indent=2)}")

    # Create response with the roast
    body = {
        "message": f"Hello {user_name}!",
    }

    # Use the wrapper function to create a properly formatted response
    return success_response(body)
