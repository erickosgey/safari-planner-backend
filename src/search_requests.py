import json
import boto3
import logging
import os
from decimal import Decimal
from botocore.exceptions import ClientError
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
requests_table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
verification_table = dynamodb.Table(os.environ['VERIFICATION_TABLE'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

def verify_code(email, code):
    """Verify the provided code for the given email."""
    try:
        # Get the verification record
        response = verification_table.get_item(
            Key={
                'email': email
            }
        )
        
        if 'Item' not in response:
            return False
        
        item = response['Item']
        
        # Check if code matches and is not expired
        if (item.get('verificationCode') == code and 
            datetime.fromisoformat(item.get('expirationTime')) > datetime.utcnow()):
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error verifying code: {str(e)}")
        return False

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
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        email = query_params.get('email')
        code = query_params.get('code')
        
        # Validate email and code
        if not email or not code:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Email and verification code are required'
                })
            }
        
        # Get verification record
        try:
            response = verification_table.get_item(
                Key={
                    'email': email
                }
            )
            verification_item = response.get('Item')
            
            if not verification_item:
                return {
                    'statusCode': 404,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'error': 'Verification code not found'
                    })
                }
            
            # Check if code matches and is not expired
            stored_code = verification_item.get('verificationCode')
            expiration_time = datetime.fromisoformat(verification_item.get('expirationTime'))
            
            if stored_code != code or datetime.utcnow() > expiration_time:
                return {
                    'statusCode': 401,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'error': 'Invalid or expired verification code'
                    })
                }
            
            # Query requests by email
            response = requests_table.query(
                IndexName='EmailIndex',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={
                    ':email': email
                }
            )
            
            items = response.get('Items', [])
            
            # Format response
            formatted_items = []
            for item in items:
                formatted_item = {
                    'requestId': item.get('requestId'),
                    'status': item.get('status'),
                    'createdAt': item.get('createdAt'),
                    'email': item.get('email'),
                    'paymentStatus': item.get('paymentStatus', 'PENDING')
                }
                
                # Include itinerary details for COMPLETE, PENDING_BOOKING, and PENDING_ACCEPTANCE statuses
                if item.get('status') in ['COMPLETE', 'PENDING_BOOKING', 'PENDING_ACCEPTANCE']:
                    formatted_item['itinerary'] = item.get('output')
                
                formatted_items.append(formatted_item)
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'requests': formatted_items
                }, cls=DecimalEncoder)
            }
            
        except ClientError as e:
            logger.error(f"Error querying DynamoDB: {str(e)}")
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'Error retrieving requests'
                })
            }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        } 