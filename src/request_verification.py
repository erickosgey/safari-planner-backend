import json
import boto3
import logging
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from mailersend import emails
from mailersend.emails import NewEmail

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
verification_table = dynamodb.Table(os.environ['VERIFICATION_TABLE'])
ssm = boto3.client('ssm')

def generate_verification_code():
    """Generate a 6-digit verification code."""
    import random
    return str(random.randint(100000, 999999))

def store_verification_code(email, code):
    """Store verification code in DynamoDB with 8-hour expiration."""
    try:
        # Calculate expiration time (8 hours from now)
        expiration_time = int((datetime.now() + timedelta(hours=8)).timestamp())
        
        # Store in DynamoDB
        verification_table.put_item(
            Item={
                'email': email,
                'code': code,
                'expiresAt': expiration_time
            }
        )
        logger.info(f"Stored verification code for {email} with expiration {expiration_time}")
        return True
    except Exception as e:
        logger.error(f"Error storing verification code: {str(e)}")
        return False

def send_verification_email(email, code):
    """Send verification email using MailerSend."""
    try:
        # Get the API key from SSM Parameter Store
        response = ssm.get_parameter(
            Name='/safari-planner/mailersend/api-key',
            WithDecryption=True
        )
        api_key = response['Parameter']['Value']
        logger.info(f"Retrieved API key from SSM Parameter Store")
        
        # Initialize MailerSend client
        mailer = NewEmail(api_key)
        logger.info("Initialized MailerSend client")
        
        # Prepare email content
        subject = "Your Great Rift Safari Verification Code"
        html_content = f"""
        <html>
            <body>
                <h2>Welcome to Great Rift Safari!</h2>
                <p>Your verification code is: <strong>{code}</strong></p>
                <p>This code will expire in 8 hours.</p>
                <p>If you didn't request this code, please ignore this email.</p>
            </body>
        </html>
        """
        
        # Create email message
        message = {
            "from": {
                "email": "noreply@greatriftsafari.com",
                "name": "Great Rift Safari"
            },
            "to": [
                {
                    "email": email
                }
            ],
            "subject": subject,
            "html": html_content
        }
        
        logger.info(f"Prepared email message for {email}")
        
        try:
            # Send email
            logger.info("Attempting to send email via MailerSend API...")
            response = mailer.send(message)
            
            # Check if response contains error information
            if isinstance(response, dict) and response.get('errors'):
                error_msg = response.get('errors', {}).get('message', 'Unknown MailerSend error')
                logger.error(f"MailerSend API error: {error_msg}")
                return False, error_msg
                
            logger.info(f"Successfully sent verification email to {email}")
            return True, None
            
        except Exception as send_error:
            error_msg = str(send_error)
            if "422" in error_msg and "verified domains" in error_msg.lower():
                error_msg = "Email service configuration error. Please contact support."
            logger.error(f"Error in mailer.send(): {error_msg}")
            logger.exception("Full send error details:")
            return False, error_msg
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error sending verification email: {error_msg}")
        logger.exception("Full error details:")
        return False, error_msg

def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With,Accept',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '600',
        'Content-Type': 'application/json'
    }

    # Handle OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }

    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        
        if not email:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Email is required'
                })
            }
        
        # Generate verification code
        code = generate_verification_code()
        
        # Store verification code
        if not store_verification_code(email, code):
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Failed to store verification code'
                })
            }
        
        # Send verification email
        success, error_msg = send_verification_email(email, code)
        if not success:
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Failed to send verification email',
                    'details': error_msg
                })
            }
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Verification code sent successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        } 