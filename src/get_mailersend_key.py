import json
import boto3
import logging
import os

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SSM client
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    try:
        # Get the API key from SSM Parameter Store
        response = ssm.get_parameter(
            Name='/safari-planner/mailersend/api-key',
            WithDecryption=True
        )
        
        api_key = response['Parameter']['Value']
        
        # Store the API key in a temporary file
        with open('/tmp/mailersend_api_key.txt', 'w') as f:
            f.write(api_key)
        
        logger.info("Successfully retrieved and stored MailerSend API key")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'API key retrieved successfully'
            })
        }
    except Exception as e:
        logger.error(f"Error retrieving API key: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to retrieve API key',
                'details': str(e)
            })
        } 