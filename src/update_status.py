import json
import logging
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

# Valid status values
VALID_STATUSES = {
    'PENDING_ITENERARY_CREATION',
    'PENDING_ITENERARY_ACCEPTANCE',
    'PENDING_BOOKING',
    'PENDING_PAYMENT',
    'COMPLETE'
}

def update_request_status(request_id: str, new_status: str) -> Dict[str, Any]:
    """Update the status of a request in DynamoDB."""
    try:
        # Validate the status
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}")
        
        # Update the request status
        response = table.update_item(
            Key={'requestId': request_id},
            UpdateExpression='SET #status = :status, updatedAt = :updatedAt',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': new_status,
                ':updatedAt': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        return response.get('Attributes', {})
        
    except Exception as e:
        logger.error(f"Error updating request status: {str(e)}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle the Lambda function invocation."""
    try:
        logger.info("Received event:")
        logger.info(json.dumps(event, indent=2))
        
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
        
        # Extract request ID from query parameters
        request_id = event.get('queryStringParameters', {}).get('requestId')
        if not request_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing requestId in query parameters'
                }),
                'headers': cors_headers
            }
        
        # Parse the request body
        try:
            body = json.loads(event.get('body', '{}'))
            new_status = body.get('status')
            if not new_status:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing status in request body'
                    }),
                    'headers': cors_headers
                }
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid JSON in request body'
                }),
                'headers': cors_headers
            }
        
        # Update the status
        try:
            updated_item = update_request_status(request_id, new_status)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Status updated successfully',
                    'requestId': request_id,
                    'status': new_status,
                    'updatedAt': updated_item.get('updatedAt')
                }),
                'headers': cors_headers
            }
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': str(e)
                }),
                'headers': cors_headers
            }
        except Exception as e:
            if 'Item not found' in str(e):
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': f'Request {request_id} not found'
                    }),
                    'headers': cors_headers
                }
            raise
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            }),
            'headers': cors_headers
        } 