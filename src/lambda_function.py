import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
import boto3
import logging
import os
import uuid
from config import (
    BEDROCK_MODEL_ID,
    BEDROCK_MAX_TOKENS,
    BEDROCK_TEMPERATURE,
    BEDROCK_TOP_P,
    BEDROCK_ANTHROPIC_VERSION,
    BEDROCK_TOP_K,
    BEDROCK_REGION,
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

# Initialize Bedrock client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.environ.get('BEDROCK_REGION', 'us-east-1')
)


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


def generate_prompt(request_data: Dict[str, Any]) -> str:
    """Generate a prompt for the Bedrock model."""
    try:
        # Extract dates from the request data
        travel_dates = request_data.get('travelDates', {})
        start_date = travel_dates.get('startDate')
        end_date = travel_dates.get('endDate')
        
        if not start_date or not end_date:
            raise ValueError("Missing start date or end date")
        
        # Calculate total number of travelers
        group = request_data.get('group', {})
        international = group.get('international', {})
        resident = group.get('resident', {})
        
        total_travelers = (
            international.get('adults', 0) +
            international.get('children', 0) +
            resident.get('adults', 0) +
            resident.get('children', 0)
        )
        
        # Build preferences string
        preferences = []
        if request_data.get('accommodation'):
            preferences.append(f"accommodation type: {request_data['accommodation']}")
        if request_data.get('interests'):
            preferences.append(f"interests: {', '.join(request_data['interests'])}")
        if request_data.get('travelStyle'):
            preferences.append(f"travel style: {request_data['travelStyle']}")
        if request_data.get('specialRequests') and request_data['specialRequests'] != "None":
            preferences.append(f"special requests: {request_data['specialRequests']}")
        
        preferences_str = ", ".join(preferences) if preferences else "no specific preferences"
        
        # Generate the prompt
        prompt = f"""Create a detailed safari itinerary for {total_travelers} travelers from {start_date} to {end_date}.
        The travelers have the following preferences: {preferences_str}. Only include destinations in Kenya.
        
        Please provide a detailed day-by-day itinerary including:
        1. Accommodation recommendations
        2. Activities and game drives
        3. Meal arrangements
        4. Transportation details
        5. Estimated costs
        
        Format the response as a JSON object with the following structure:
        {{
            "summary": "Brief overview of the safari",
            "itinerary": [
                {{
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "activities": [
                        {{
                            "time": "HH:MM",
                            "description": "Activity description",
                            "location": "Location name"
                        }}
                    ],
                    "accommodation": {{
                        "name": "Lodge/Camp name",
                        "type": "Lodge/Camp type",
                        "location": "Location"
                    }},
                    "meals": ["Breakfast", "Lunch", "Dinner"]
                }}
            ],
            "totalCost": 0,
            "costPerPerson": 0,
            "inclusions": ["List of what's included"],
            "exclusions": ["List of what's not included"],
            "notes": ["Important notes and recommendations"]
        }}"""
        
        return prompt
        
    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        raise


def generate_itinerary(prompt: str) -> Dict[str, Any]:
    """Generate an itinerary using the Bedrock model."""
    try:
        # Prepare the request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 250,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Log the request
        logger.info(f"Sending request to Bedrock: {json.dumps(request_body)}")
        
        # Invoke the model
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response.get('body').read())
        generated_text = response_body['content'][0]['text']
        
        # Log the raw response
        logger.info(f"Received response from Bedrock: {generated_text}")
        
        # Find the JSON content in the response
        try:
            # Look for JSON content between ```json and ``` markers
            if '```json' in generated_text:
                json_start = generated_text.find('```json') + 7
                json_end = generated_text.find('```', json_start)
                json_str = generated_text[json_start:json_end].strip()
            else:
                # If no markers, try to find the first { and last }
                json_start = generated_text.find('{')
                json_end = generated_text.rfind('}') + 1
                json_str = generated_text[json_start:json_end].strip()
            
            # Parse the JSON
            itinerary = json.loads(json_str)
            
            # Validate the structure
            if not isinstance(itinerary, dict):
                raise ValueError("Generated itinerary is not a valid JSON object")
            
            if 'itinerary' not in itinerary:
                raise ValueError("Generated itinerary missing 'itinerary' array")
            
            # Calculate total cost if not provided
            if 'totalCost' not in itinerary:
                total_cost = sum(day.get('totalCost', 0) for day in itinerary['itinerary'])
                itinerary['totalCost'] = total_cost
            
            # Calculate cost per person if not provided
            if 'costPerPerson' not in itinerary:
                itinerary['costPerPerson'] = itinerary['totalCost'] / total_travelers
            
            return itinerary
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from response: {str(e)}")
            raise ValueError(f"Failed to parse JSON from model response: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}")
        raise


def store_request(request_data: SafariRequest, itinerary_data: Dict[str, Any] = None, error_message: str = None) -> str:
    """Store the safari request in DynamoDB."""
    request_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    item = {
        'requestId': request_id,
        'email': request_data.email,
        'createdAt': now,
        'startDate': request_data.travelDates.startDate.isoformat(),
        'endDate': request_data.travelDates.endDate.isoformat(),
        'status': 'pending',  # Initial status
        'paymentStatus': 'unpaid',
        'totalCost': 0,  # Will be updated when itinerary is generated
        'costPerPerson': 0,
        'currency': 'USD',
        'input': request_data.model_dump_json(),
        'output': None,  # Will be updated when itinerary is generated
        'errorMessage': error_message,
        'payment': {
            'status': 'unpaid',
            'totalDue': 0,
            'currency': 'USD',
            'installments': []
        }
    }
    
    try:
        table.put_item(Item=item)
        logger.info(f"Stored request {request_id} in DynamoDB")
        return request_id
    except Exception as e:
        logger.error(f"Failed to store request in DynamoDB: {str(e)}")
        raise


def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    try:
        logger.info("Received event:")
        logger.info(json.dumps(event, indent=2))

        # Handle both direct invocations and API Gateway requests
        if isinstance(event, dict):
            if "body" in event:
                # API Gateway request
                try:
                    parsed_body = json.loads(event["body"])
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse request body: {str(e)}")
                    return {
                        "statusCode": 400,
                        "body": json.dumps({"error": "Invalid JSON in request body"}),
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*"
                        }
                    }
            else:
                # Direct Lambda invocation
                parsed_body = event
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid request format"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

        try:
            request_data = SafariRequest(**parsed_body)
        except Exception as e:
            error_msg = f"Invalid request data: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

        # Store initial request
        request_id = store_request(request_data)

        # Invoke the processing function asynchronously
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName=os.environ['PROCESS_FUNCTION_NAME'],
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps({
                'requestId': request_id,
                'requestData': request_data.model_dump_json()  # Use model_dump_json() instead of model_dump()
            })
        )

        # Return the request ID immediately
        return {
            "statusCode": 202,  # Accepted
            "body": json.dumps({
                "requestId": request_id,
                "status": "pending",
                "message": "Your request is being processed. Use the requestId to check the status."
            }),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
