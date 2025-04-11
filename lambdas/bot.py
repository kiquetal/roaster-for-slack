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

def create_roast_prompt(user_name, user_attributes, tickets):
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
    Eres un comediante, que se burla de otra persona, pero sin ser muy ofensivo, usas
    un conjunto de descripciones a tareas asignadas en un ambiente de desarollo de software
    Usa siempre algunas de estas caracteristicas:
    
    {attributes_text}

    Tambien burlate de las descripciones de las tareas que se encuentran en  
    
    {tickets}
    
    Trata de usar caracteristicas de los tickets
    
   La burla debe ser humorosa, no tan agresiva,  no escribas mas de 150 palabras
   Agrega un emoji al final
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
        model_id = "anthropic.claude-v2:1"

        # Format the prompt for Claude model and explicitly instruct to respond in Spanish
        formatted_prompt = f"\n\nHuman:{prompt}\n\nPor favor, responde en español.\n\nAssistant:"

        # Prepare the request body
        request_body = {
            "prompt": formatted_prompt,
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


def obtainTicketsForUsersId(user_id):
    """
    Obtain tickets for a given user ID from DynamoDB.

    Args:
        user_id (str): The user's ID

    Returns:
        list: List of tickets for the user
    """
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get('DYNAMODB_TABLE', 'roaster-for-slack-conversation-context')
    table = dynamodb.Table(table_name)

    # Query the DynamoDB table for tickets
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        & boto3.dynamodb.conditions.Key('sk').begins_with('#TICKET#')

    )

    # Extract tickets from the response
    tickets = response.get('Items', [])
    return tickets


def hello(event, context):
    # Extract user information from the event
    user_id = None
    user_name = "User"

    # Parse the event body if it exists
    if event.get('body'):
        try:
            # Check if the body is Base64 encoded
            body = event['body']
            if event.get('isBase64Encoded', False):
                import base64
                body = base64.b64decode(body).decode('utf-8')

            # Try to parse as JSON first
            try:
                body_json = json.loads(body)
                # Extract user_id from Slack event
                if 'event' in body_json and 'user' in body_json['event']:
                    user_id = body_json['event']['user']
                elif 'user_id' in body_json:
                    user_id = body_json['user_id']
            except json.JSONDecodeError:
                # If not JSON, try to parse as URL-encoded form data
                import urllib.parse
                form_data = dict(urllib.parse.parse_qsl(body))
                if 'user_id' in form_data:
                    user_id = form_data['user_id']
                if 'user_name' in form_data:
                    user_name = form_data['user_name']
        except (KeyError, Exception) as e:
            print(f"Error parsing event body: {e}")

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

                tickets = obtainTicketsForUsersId(user_id)
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
    prompt = create_roast_prompt(user_name, user_attributes, tickets)

    # Call Bedrock to generate a roast
    roast = generate_roast(prompt)


    # Print the user attributes obtained from DynamoDB
    print(f"User attributes from DynamoDB: {json.dumps(user_attributes, indent=2)}")

    message = roast if roast else "No pude crear una broma esta vez. Por favor, inténtalo de nuevo más tarde."
    # Reply to the Slack channel
    if 'body' in event and user_id:
        try:
            # Parse the event body to get the channel ID
            body = event['body']
            if event.get('isBase64Encoded', False):
                import base64
                body = base64.b64decode(body).decode('utf-8')

            channel_id = None
            try:
                body_json = json.loads(body)
                if 'event' in body_json and 'channel' in body_json['event']:
                    channel_id = body_json['event']['channel']
            except json.JSONDecodeError:
                import urllib.parse
                form_data = dict(urllib.parse.parse_qsl(body))
                if 'channel_id' in form_data:
                    channel_id = form_data['channel_id']

            # Send message to the channel
            if channel_id and slack_token:
                client = WebClient(token=slack_token)
                response = client.chat_postMessage(
                    channel=channel_id,
                    text=message
                )
                print(f"Message sent to channel: {channel_id}")
        except Exception as e:
            print(f"Error sending message to Slack channel: {e}")

    # Create response with the message
    body = {
        "message": message,
    }

    # Use the wrapper function to create a properly formatted response
    return success_response(body)
