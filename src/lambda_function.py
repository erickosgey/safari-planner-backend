import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
import boto3
import logging
import os
import uuid

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

class TravelDates(BaseModel):
    startDate: date
    endDate: date
    isFlexible: bool

    model_config = ConfigDict(json_encoders={date: lambda v: v.isoformat()})


class GroupMember(BaseModel):
    adults: int = Field(ge=0)
    children: int = Field(ge=0)


class Group(BaseModel):
    international: GroupMember
    resident: GroupMember


class SafariRequest(BaseModel):
    travelDates: TravelDates
    group: Group
    accommodation: str
    interests: List[str]
    travelStyle: str
    email: str
    specialRequests: str

    model_config = ConfigDict(json_encoders={date: lambda v: v.isoformat()})


def store_request(request_data: SafariRequest, itinerary_data: Dict[str, Any] = None, error_message: str = None) -> str:
    """Store the safari request in DynamoDB."""
    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    # Convert request data to dict and ensure dates are serialized
    request_dict = request_data.model_dump()
    request_dict['travelDates']['startDate'] = request_dict['travelDates']['startDate'].isoformat()
    request_dict['travelDates']['endDate'] = request_dict['travelDates']['endDate'].isoformat()
    
    item = {
        'requestId': request_id,
        'email': request_data.email,
        'createdAt': now,
        'startDate': request_dict['travelDates']['startDate'],
        'endDate': request_dict['travelDates']['endDate'],
        'status': 'pending',  # Initial status
        'paymentStatus': 'unpaid',
        'totalCost': 0,  # Will be updated when itinerary is generated
        'costPerPerson': 0,
        'currency': 'USD',
        'input': json.dumps(request_dict),
        'output': None,  # Will be updated when itinerary is generated
        'errorMessage': error_message,
        'payment': {
            'status': 'unpaid',
            'totalDue': 0,
            'currency': 'USD',
            'installments': []
        }
    }
    
    if itinerary_data:
        item['output'] = json.dumps(itinerary_data)
        item['status'] = 'complete'
        item['totalCost'] = itinerary_data.get('totalCost', 0)
        item['costPerPerson'] = itinerary_data.get('costPerPerson', 0)
        item['payment']['totalDue'] = item['totalCost']
    
    try:
        table.put_item(Item=item)
        return request_id
    except Exception as e:
        logger.error(f"Error storing request: {str(e)}")
        raise


def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    try:
        logger.info("Received new request")
        logger.debug(f"Event details: {json.dumps(event, indent=2)}")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        logger.debug(f"Parsed request body: {json.dumps(body, indent=2)}")
        
        # Validate request data
        try:
            logger.info("Validating request data")
            request_data = SafariRequest(**body)
            logger.debug(f"Validated request data: {request_data.model_dump_json(indent=2)}")
        except Exception as e:
            error_msg = f"Invalid request data: {str(e)}"
            logger.error(error_msg)
            logger.exception("Validation error details:")
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid request data',
                    'details': str(e)
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Store initial request
        logger.info("Storing initial request")
        request_id = store_request(request_data)
        logger.info(f"Request stored with ID: {request_id}")
        
        # Invoke the processing function asynchronously
        logger.info(f"Invoking process_itinerary function for request {request_id}")
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName=os.environ['PROCESS_FUNCTION_NAME'],
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({
                'requestId': request_id,
                'requestData': request_data.model_dump_json()
            })
        )
        logger.info(f"Successfully invoked process_itinerary function for request {request_id}")
        
        # Return success response
        logger.info(f"Returning success response for request {request_id}")
        return {
            'statusCode': 202,  # Accepted
            'body': json.dumps({
                'requestId': request_id,
                'status': 'pending',
                'message': 'Your request is being processed. Use the requestId to check the status.'
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full error details:")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
