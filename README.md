# Roaster for Slack

A serverless application that integrates Amazon Bedrock with Slack, allowing users to interact with AI models through a Slack bot.

## Project Overview

This project enables users to invoke Amazon Bedrock AI models directly from a Slack channel. The application:

1. Receives messages from a Slack bot
2. Stores conversation context in DynamoDB
3. Sends the context and user message to Amazon Bedrock
4. Returns the AI response back to the Slack channel

## Architecture

The application is built using:

- **AWS Lambda**: Serverless functions to handle requests
- **Amazon Bedrock**: AI model service for generating responses
- **Amazon DynamoDB**: NoSQL database for storing conversation context
- **Slack API**: For bot integration with Slack channels
- **Serverless Framework**: For infrastructure as code deployment

## Project Structure

```
roaster-for-slack/
├── lambdas/                # Lambda function implementations
│   ├── __init__.py         # Makes the directory a Python package
│   └── hello.py            # Example lambda function
├── response/               # Response formatting utilities
│   ├── __init__.py         # Makes the directory a Python package
│   └── wrapper.py          # Response wrapper functions
├── handler.py              # Main handler that routes to specific lambdas
├── serverless.yml          # Serverless Framework configuration
└── README.md               # Project documentation
```

## DynamoDB Schema

The application uses a DynamoDB table to store conversation context with the following schema:

| Attribute      | Type   | Description                                |
|----------------|--------|--------------------------------------------|
| user_id        | String | Primary key - Slack user ID                |
| conversation_id| String | Sort key - Unique conversation identifier  |
| messages       | List   | Array of previous messages in conversation |
| timestamp      | Number | Last update timestamp                      |
| metadata       | Map    | Additional user/conversation metadata      |

## Setup and Deployment

### Prerequisites

- Node.js and npm
- Serverless Framework CLI
- AWS CLI configured with appropriate permissions
- Slack workspace with bot creation permissions

### Slack Bot Setup

1. Go to [Slack API Apps page](https://api.slack.com/apps) and create a new app
2. Under "OAuth & Permissions", add the following scopes:
   - `users:read` - To fetch user information
   - `chat:write` - To send messages
   - `app_mentions:read` - To receive mention events
3. Install the app to your workspace
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`) to use as your SLACK_OAUTH_TOKEN

### Dependencies

The project uses the following plugins:
- **serverless-layer-requirements**: Automatically creates a Lambda layer from Python requirements.txt

Python dependencies are managed in the `requirements.txt` file and include:
- boto3: AWS SDK for Python
- slack_sdk: Slack API SDK for Python

### Deployment

1. Install Serverless Framework plugins:
   ```
   npm install --save-dev serverless-layer-requirements
   ```

2. Update Python dependencies (if needed):
   ```
   # Edit requirements.txt to add or update dependencies
   ```

3. Set up the Slack OAuth token:
   ```
   # Set the environment variable for deployment
   export SLACK_OAUTH_TOKEN=xoxb-your-token-here
   ```

4. Deploy to AWS:
   ```
   serverless deploy
   ```

5. Configure the Slack bot with the generated API endpoint

## Development

To add new lambda functions:

1. Create a new file in the `lambdas/` directory
2. Update the `serverless.yml` file to include the new function
3. Import and use the function in `handler.py`

## Content Moderation

The bot uses Amazon Bedrock's Claude model to generate roasts. Claude has built-in content moderation that may refuse to generate content it considers inappropriate or harmful. When this happens:

1. The bot detects refusal messages from Claude by checking for common refusal phrases
2. Instead of showing the raw refusal message to users, the bot provides a friendly message explaining that it can't generate the requested content
3. The friendly message is in Spanish to match the language of the roasts: "Lo siento, no puedo generar una broma que pueda resultar ofensiva. ¿Qué tal si intentamos algo diferente? 😊"

This ensures a better user experience even when content moderation is triggered.

## License

[License information]
