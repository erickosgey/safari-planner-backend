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

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    try:
        logger.info("Received event:")
        logger.info(json.dumps(event, indent=2))
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        email = query_params.get('email')
        
        # Return empty result if no email is provided
        if not email:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({
                    'items': [],
                    'count': 0
                })
            }
        
        # Query DynamoDB using email index
        response = table.query(
            IndexName='EmailIndex',
            KeyConditionExpression=Key('email').eq(email)
        )
        
        # Process and format the response
        items = response.get('Items', [])
        
        # Sort items by createdAt in descending order
        items.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        # Format the response with only the requested fields
        formatted_items = []
        for item in items:
            formatted_item = {
                'requestId': item.get('requestId'),
                'status': item.get('status'),
                'startDate': item.get('startDate'),
                'endDate': item.get('endDate'),
                'createdAt': item.get('createdAt')
            }
            formatted_items.append(formatted_item)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'items': formatted_items,
                'count': len(formatted_items)
            }, cls=DecimalEncoder)
        }

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Error accessing database',
                'details': str(e)
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        } 