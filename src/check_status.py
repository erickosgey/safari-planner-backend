import json
import boto3
import logging
import os
from decimal import Decimal
from botocore.exceptions import ClientError

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
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
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
        query_params = event.get('queryStringParameters', {}) or {}
        request_id = query_params.get('requestId')
        if not request_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing requestId in query parameters'
                }),
                'headers': cors_headers
            }
        
        # Query DynamoDB for the request
        try:
            response = table.get_item(Key={'requestId': request_id})
            item = response.get('Item')
            
            if not item:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': f'Request {request_id} not found'
                    }),
                    'headers': cors_headers
                }
            
            # Prepare the response data
            response_data = {
                'requestId': item.get('requestId'),
                'status': item.get('status'),
                'createdAt': item.get('createdAt'),
                'startDate': item.get('startDate'),
                'endDate': item.get('endDate'),
                'email': item.get('email'),
                'totalCost': item.get('totalCost', 0),
                'costPerPerson': item.get('costPerPerson', 0),
                'currency': item.get('currency', 'USD'),
                'paymentStatus': item.get('paymentStatus', 'unpaid')
            }
            
            # Include itinerary details for COMPLETE and PENDING_BOOKING statuses
            status = str(item.get('status', '')).upper()
            logger.info(f"Current status: {status}")
            logger.info(f"Itinerary present: {'itinerary' in item}")
            
            if status in ['COMPLETE', 'PENDING_BOOKING'] and 'itinerary' in item:
                response_data['itinerary'] = item['itinerary']
                logger.info("Included itinerary in response")
            else:
                logger.info(f"Not including itinerary. Status: {status}, Has itinerary: {'itinerary' in item}")
            
            # Include error message if status is error
            if status == 'ERROR':
                response_data['errorMessage'] = item.get('errorMessage')
            
            return {
                'statusCode': 200,
                'body': json.dumps(response_data, cls=DecimalEncoder),
                'headers': cors_headers
            }
            
        except Exception as e:
            logger.error(f"Error querying DynamoDB: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal server error'
                }),
                'headers': cors_headers
            }
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            }),
            'headers': cors_headers
        } 