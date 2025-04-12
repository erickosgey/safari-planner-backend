import json
import boto3
import logging
import os
from decimal import Decimal
from botocore.exceptions import ClientError

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
        
        # Extract request ID from path parameters
        request_id = event.get('pathParameters', {}).get('requestId')
        if not request_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing requestId in path parameters'
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
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
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
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
            if item.get('status') in ['COMPLETE', 'PENDING_BOOKING'] and 'itinerary' in item:
                response_data['itinerary'] = item['itinerary']
            
            # Include error message if status is error
            if item.get('status') == 'error':
                response_data['errorMessage'] = item.get('errorMessage')
            
            return {
                'statusCode': 200,
                'body': json.dumps(response_data, cls=DecimalEncoder),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
            
        except Exception as e:
            logger.error(f"Error querying DynamoDB: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal server error'
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        } 