import json

def format_response(status_code, body):
    """
    Format a response for API Gateway
    
    Args:
        status_code (int): HTTP status code
        body (dict): Response body
        
    Returns:
        dict: Formatted response
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }

def success_response(body):
    """
    Create a success response
    
    Args:
        body (dict): Response body
        
    Returns:
        dict: Formatted success response
    """
    return format_response(200, body)

def error_response(message, status_code=400):
    """
    Create an error response
    
    Args:
        message (str): Error message
        status_code (int): HTTP status code
        
    Returns:
        dict: Formatted error response
    """
    return format_response(status_code, {"error": message})
