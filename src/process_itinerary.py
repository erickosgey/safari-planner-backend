import json
import boto3
import logging
import os
from decimal import Decimal
from botocore.exceptions import ClientError
from typing import Dict, Any
from datetime import datetime
from config import (
    BEDROCK_MODEL_ID,
    BEDROCK_MAX_TOKENS,
    BEDROCK_TEMPERATURE,
    BEDROCK_TOP_P,
    BEDROCK_TOP_K,
    BEDROCK_ANTHROPIC_VERSION,
    BEDROCK_REGION,
    BEDROCK_INFERENCE_PROFILE
)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Bedrock client
bedrock = boto3.client(
    'bedrock-runtime',
    region_name=BEDROCK_REGION
)

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
        prompt = f"""
You are a professional safari itinerary planner and cost estimator.

Create a detailed safari itinerary for {total_travelers} travelers from {start_date} to {end_date}.
Traveler preferences: {preferences_str}
Destination constraint: ONLY Kenya.

----------------------------------------
SEASONAL RATE RULES
----------------------------------------
- Determine correct seasonal rate based on travel dates.
- If trip spans seasons, calculate nightly cost per applicable season.
- If a rate is given as a range, use the LOWER bound.
- If seasonal overlap unclear, use the higher applicable rate.

----------------------------------------
ROOM RATE CONVERSION RULES
----------------------------------------
- Per person per night → use directly.
- Double room per night → divide by 2.
- Room rate ranges → use lower bound.
- Always calculate cost per person per night before totals.

----------------------------------------
COST CALCULATION RULES
----------------------------------------
Include:
- Accommodation
- Transportation between parks
- Shared safari vehicle with driver-guide
- Game drives
- Meals (if not included in lodge rate)

Exclude (must list in exclusions):
- Park entry fees
- International flights
- Visa fees
- Travel insurance
- Personal expenses

----------------------------------------
UPDATED ACCOMMODATION DATABASE (Realistic Public Market Ranges)
----------------------------------------

MAASAI MARA – LUXURY

Angama Mara  
~1800 USD+ per person per night (fully inclusive)

Mahali Mzuri  
~1100–1800 USD per person per night

Cottar's 1920s Safari Camp  
~1200–2000 USD per person per night

----------------------------------------

MAASAI MARA – MID RANGE

Mara Serena Safari Lodge  
Low/Shoulder: 260 USD double room/night  
High/Peak: 410 USD double room/night  

Keekorok Lodge  
Low: 300 USD double room/night  
High: 350 USD double room/night  

Mara Sopa Lodge  
Low: 230 USD double room/night  
High: 285 USD double room/night  

----------------------------------------

MAASAI MARA – BUDGET

Enchoro Wildlife Camp  
65–90 USD per person per night  

Masai Mara Manyatta Camp  
90–120 USD per person per night  

Oldarpoi Mara Camp  
70–100 USD per person per night  

----------------------------------------

AMBOSELI

Amboseli Serena Safari Lodge  
Low: 300 USD double room/night  
High: 530 USD double room/night  

Kibo Safari Camp  
150–190 USD per person per night  

----------------------------------------

TSAVO

Voi Wildlife Lodge  
100–150 USD per person per night  

Kilaguni Serena Safari Lodge  
300–450 USD double room/night  

----------------------------------------

LAKE NAKURU / NAIVASHA

Lake Naivasha Sopa Resort  
Low: 140 USD per person per night  
High: 230 USD per person per night  

Sarova Lion Hill Game Lodge  
350–450 USD double room/night  

The Cliff Nakuru  
880–1100 USD double tent/night  

----------------------------------------

NAIROBI

Giraffe Manor  
800–1500 USD per person per night  

Hemingways Nairobi  
600 USD double suite/night  

Sarova Stanley Hotel  
180–350 USD double room/night  

----------------------------------------
OUTPUT FORMAT
----------------------------------------

Return ONLY valid JSON. No markdown. No explanations.
All monetary values must be numeric. Round to 2 decimal places.

Structure (use exactly this schema):

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
}}
"""
        return prompt

    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        raise


def _normalize_itinerary_schema(itinerary: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the committed JSON schema keys so API response format stays unchanged."""
    allowed_top = {"summary", "itinerary", "totalCost", "costPerPerson", "inclusions", "exclusions", "notes"}
    allowed_day = {"day", "date", "activities", "accommodation", "meals"}
    allowed_activity = {"time", "description", "location"}
    allowed_accommodation = {"name", "type", "location"}

    out = {k: itinerary[k] for k in allowed_top if k in itinerary}
    if "itinerary" in out:
        out["itinerary"] = []
        for day in itinerary["itinerary"]:
            d = {k: day[k] for k in allowed_day if k in day}
            if "activities" in d:
                d["activities"] = [
                    {k: a[k] for k in allowed_activity if k in a}
                    for a in day["activities"]
                ]
            if "accommodation" in d and isinstance(day["accommodation"], dict):
                d["accommodation"] = {
                    k: day["accommodation"][k]
                    for k in allowed_accommodation
                    if k in day["accommodation"]
                }
            out["itinerary"].append(d)
    return out


def generate_itinerary(prompt: str, total_travelers: int = 1) -> Dict[str, Any]:
    """Generate an itinerary using the Bedrock model."""
    try:
        # Prepare the request body with configurations from config.py
        request_body = {
            "anthropic_version": BEDROCK_ANTHROPIC_VERSION,
            "max_tokens": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
            "top_p": BEDROCK_TOP_P,
            "top_k": BEDROCK_TOP_K,
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
            modelId=BEDROCK_INFERENCE_PROFILE,
            body=json.dumps(request_body),
            performanceConfigLatency="optimized"
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
                itinerary['totalCost'] = sum(
                    day.get('totalCost', 0) for day in itinerary['itinerary']
                )

            # Calculate cost per person if not provided
            if 'costPerPerson' not in itinerary and total_travelers:
                itinerary['costPerPerson'] = itinerary['totalCost'] / total_travelers

            # Return only the committed schema (drop any extra keys from LLM)
            return _normalize_itinerary_schema(itinerary)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from response: {str(e)}")
            raise ValueError(f"Failed to parse JSON from model response: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}")
        raise

def update_request_status(request_id, status, itinerary_data=None, error=None):
    """Update the status of a request in DynamoDB."""
    try:
        logger.info(f"Updating request {request_id} status to {status}")
        logger.debug(f"Status update details - itinerary_data: {itinerary_data}, error: {error}")
        
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
            # Convert Decimal values to float for JSON serialization
            serialized_itinerary = json.loads(json.dumps(itinerary_data, default=str))
            
            update_expression += ", #output = :output, totalCost = :totalCost, costPerPerson = :costPerPerson"
            expression_values.update({
                ':output': serialized_itinerary,
                ':totalCost': Decimal(str(serialized_itinerary.get('totalCost', 0))),
                ':costPerPerson': Decimal(str(serialized_itinerary.get('costPerPerson', 0)))
            })
            expression_names['#output'] = 'output'
            logger.debug(f"Adding itinerary data to update: {json.dumps(serialized_itinerary, indent=2)}")
        
        if error:
            update_expression += ", #error_message = :error_message"
            expression_values[':error_message'] = str(error)
            expression_names['#error_message'] = 'error'
            logger.debug(f"Adding error message to update: {error}")
        
        logger.debug(f"Update expression: {update_expression}")
        # Convert Decimal values to float for logging
        log_values = {k: float(v) if isinstance(v, Decimal) else v for k, v in expression_values.items()}
        logger.debug(f"Expression values: {json.dumps(log_values, indent=2)}")
        logger.debug(f"Expression names: {json.dumps(expression_names, indent=2)}")
        
        table.update_item(
            Key={'requestId': request_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        logger.info(f"Successfully updated request {request_id} status to {status}")
    except Exception as e:
        logger.error(f"Error updating request status: {str(e)}")
        raise

def lambda_handler(event, context):
    """Handle the Lambda function invocation."""
    try:
        logger.info("Received event for processing")
        logger.debug(f"Event details: {json.dumps(event, indent=2)}")
        
        # Extract request ID and data from the event payload
        request_id = event.get('requestId')
        request_data = json.loads(event.get('requestData', '{}'))
        
        logger.info(f"Processing request {request_id}")
        logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")
        
        if not request_id or not request_data:
            error_msg = 'Missing requestId or requestData'
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': error_msg
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                }
            }
        
        # Update request status to processing
        logger.info(f"Updating request {request_id} status to processing")
        update_request_status(request_id, 'processing')
        
        try:
            # Generate prompt
            logger.info("Generating prompt for itinerary")
            prompt = generate_prompt(request_data)
            logger.debug(f"Generated prompt: {prompt}")

            group = request_data.get('group', {})
            international = group.get('international', {})
            resident = group.get('resident', {})
            total_travelers = max(
                1,
                international.get('adults', 0) + international.get('children', 0)
                + resident.get('adults', 0) + resident.get('children', 0)
            )

            # Generate itinerary
            logger.info("Generating itinerary using Bedrock")
            itinerary = generate_itinerary(prompt, total_travelers)
            logger.debug(f"Generated itinerary: {json.dumps(itinerary, indent=2)}")
            
            # Store the itinerary
            logger.info(f"Storing itinerary for request {request_id}")
            update_request_status(request_id, 'PENDING_ACCEPTANCE', itinerary)
            logger.info(f"Successfully stored itinerary for request {request_id}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'requestId': request_id,
                    'status': 'PENDING_ACCEPTANCE',
                    'message': 'Itinerary generated successfully'
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to generate itinerary: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full error details:")
            
            # Update request status to failed
            update_request_status(request_id, 'failed', error=str(e))
            
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to generate itinerary',
                    'details': str(e)
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS'
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
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            }
        }