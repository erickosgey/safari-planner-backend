import json
import boto3
import logging
import os
from decimal import Decimal
from botocore.exceptions import ClientError
from lambda_function import generate_prompt, generate_itinerary

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def update_request_status(request_id, status, itinerary_data=None, error=None):
    """Update the status of a request in DynamoDB."""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
        
        update_expression = "SET #status = :status"
        expression_values = {
            ':status': status
        }
        expression_names = {
            '#status': 'status'
        }
        
        if itinerary_data:
            update_expression += ", itinerary = :itinerary, totalCost = :totalCost, costPerPerson = :costPerPerson"
            expression_values.update({
                ':itinerary': itinerary_data,
                ':totalCost': Decimal(str(itinerary_data.get('totalCost', 0))),
                ':costPerPerson': Decimal(str(itinerary_data.get('costPerPerson', 0)))
            })
        
        if error:
            update_expression += ", #error_message = :error_message"
            expression_values[':error_message'] = str(error)
            expression_names['#error_message'] = 'error'
        
        table.update_item(
            Key={'requestId': request_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        logger.info(f"Updated request {request_id} status to {status}")
    except Exception as e:
        logger.error(f"Error updating request status: {str(e)}")
        raise

def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    try:
        logger.info("Received event:")
        logger.info(json.dumps(event, indent=2))

        # Parse the event data
        if isinstance(event, str):
            event = json.loads(event)
        
        # Extract request ID and data
        request_id = event.get('requestId')
        request_data = event.get('requestData')
        
        if not request_id or not request_data:
            logger.error("Missing requestId or requestData in event")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields"})
            }
        
        # Parse request data if it's a string
        if isinstance(request_data, str):
            request_data = json.loads(request_data)
        
        # Update status to processing
        update_request_status(request_id, "processing")
        
        try:
            # Generate the prompt
            prompt = generate_prompt(request_data)
            
            # Generate the itinerary
            itinerary = generate_itinerary(prompt)
            
            # Update status to complete with itinerary
            update_request_status(request_id, "complete", itinerary)
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "requestId": request_id,
                    "status": "complete"
                })
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating itinerary: {error_msg}")
            update_request_status(request_id, "error", error=error_msg)
            raise
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        } 