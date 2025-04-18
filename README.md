# Roaster for Slack

A serverless application that integrates Amazon Bedrock with Slack, allowing users to interact with AI models through a Slack bot.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [DynamoDB Schema](#dynamodb-schema)
  - [Data Collected from Slack](#data-collected-from-slack)
- [Prerequisites](#prerequisites)
- [Slack Bot Setup](#slack-bot-setup)
- [Dependencies](#dependencies)
- [Deployment](#deployment)
- [Development](#development)
- [Content Moderation](#content-moderation)
- [API Endpoints](#api-endpoints)
- [License](#license)

## Project Overview

This project enables users to invoke Amazon Bedrock AI models directly from a Slack channel. The application:

1. Receives messages from a Slack bot
2. Stores profile from slack in DynamoDB
3. Generate some tickets and the use them to generate a roast
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
│   ├── bot.py              # Main roast generation function
│   └── pic.py               # Generation of images with amazon bedrock
├── response/               # Response formatting utilities
│   └── wrapper.py          # Response wrapper functions
├── serverless.yml          # Serverless Framework configuration
└── README.md               # Project documentation
```

## DynamoDB Schema

The application uses a DynamoDB table to store conversation context with the following schema:

| Attribute              | Type   | Description                  |
|------------------------|--------|------------------------------|
| user_id                | String | Primary key - Slack user ID  |
| sk                     | String | Sort key - Ticket or profile |
----------------------- |--------|--------------------------------

### Data Collected from Slack

When a user interacts with the bot, the following data is collected from Slack and stored in DynamoDB:

1. **User Profile Information**:
   - `display_name`: User's display name in Slack
   - `status_text`: User's current status message
   - `status_emoji`: User's current status emoji
   - `title`: User's job title or role
   - `phone`: User's phone number (if available in Slack profile)
   - `email`: User's email address (if available in Slack profile)
   - `image_original`: URL to user's profile image (original size)
   - `image_72`: URL to user's profile image (72x72 px)

2. **Record Structure**:
   - For user profiles:
     ```
     {
       'user_id': '<Slack user ID>',
       'sk': '#USER#<user_name>',
       'attributes': {<Slack profile data>},
       'updated_at': '<timestamp>'
     }
     ```
   
   - For tickets:
     ```
     {
       'user_id': '<Slack user ID>',
       'sk': '#TICKET#<ticket_id>',
       'comments': '<ticket content>'
     }
     ```

3. **Data Usage**:
   - User profile data is used to personalize roasts
   - Ticket information (up to 4 recent tickets) is used to generate context-aware roasts
   - All data is stored with the user's Slack ID as the primary key for efficient retrieval

This data collection is designed to enhance the user experience by creating personalized roasts based on both profile information and recent tasks/tickets.

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
   - `files:write` - To upload files-images
   - `app_mentions:read` - To receive mention events
3. Install the app to your workspace
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`) to use as your SLACK_OAUTH_TOKEN

### Dependencies

The project uses the following plugins:
- **serverless-python-requirements**: Automatically creates a Lambda layer from Python requirements.txt

Python dependencies are managed in the `requirements.txt` file and include:
- boto3: AWS SDK for Python
- slack_sdk: Slack API SDK for Python
- slack_bolt: Slack app framework for Python

### Deployment

1. Install Serverless Framework plugins:
   ```
    serverless plugin install -n serverless-python-requirements
    ```

2. Update Python dependencies (if needed):
   ```
   # Edit requirements.txt to add or update dependencies
   ```

3. Set up the Slack OAuth token:
   ```
   # Set the environment variable for deployment
   export SLACK_OAUTH_TOKEN=xoxb-your-token-here
   export SLACK_SIGNING_SECRET=your-signing-secret
   
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


## API Endpoints

The following table shows the API endpoints and their corresponding Lambda functions:

| API Path | Invoked Lambda |
|----------|---------------|
| /        | lambdas/bot.lambda_handler |
| /pic     | lambdas/pic.lambda_handler |

## License

[License information]

`
