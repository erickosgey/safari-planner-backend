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
        prompt = f"""Create a detailed safari itinerary for {total_travelers} travelers from {start_date} to {end_date}.
        The travelers have the following preferences: {preferences_str}. Only include destinations in Kenya.
        
        Please provide a detailed day-by-day itinerary including:
        1. Accommodation recommendations
        2. Activities and game drives
        3. Meal arrangements
        4. Transportation details
        5. Estimated costs
        4. Mention that park fees are exclude from the total cost

        When calculating the total cost, be sure to include:
        - Accommodation costs based on the verified rates provided
        - Daily transportation cost of $250 per vehicle per day (assume one vehicle seats up to 6 travelers)
        - Add a 20% surcharge for the safari company's service fee
        
        2. Hotel/Lodge Requirements:
        Use the following verified rates for April 2025 when calculating costs and selecting accommodations. Pay special attention to the season dates to determine the correct rate:

        Maasai Mara Luxury Options:
        - Mahali Mzuri: High Season (Jul-Oct) ~$1,780+ USD per person per night; Low Season (Apr-May, Nov) ~$1,120+ USD per person per night
        - Angama Mara: High (Jul 1–Oct 31, Dec 21–Jan 5) $2,050 USD per person per night; Low (Apr 1–May 31, Nov 1–Dec 20) $1,400 USD per person per night; Shoulder (Jan 6–Mar 31, Jun 1–Jun 30) $1,750 USD per person per night
        - Cottar's 1920s Safari Camp: Peak (Jul 1-Oct 31, Dec 20-Jan 2) $2,073 USD per person per night; High (Jan 3-Mar 31, Jun 1-Jun 30, Nov 1-Dec 19) $1,577 USD per person per night; Green/Low (Apr 1-May 31) $1,258 USD per person per night

        Maasai Mara Mid-range Options:
        - Mara Sopa Lodge: High (Jul 1-Oct 31) $285 USD per person per night; Low (Apr 1-Jun 30) $180 USD per person per night; Shoulder (Jan 3-Mar 31, Nov 1-Dec 22) $210 USD per person per night; Peak (Dec 23-Jan 2) $310 USD per person per night
        - Keekorok Lodge: High (Jul-Oct, late Dec) ~$450-600+ USD double room/night; Low (Apr-Jun) ~$300-450+ USD double room/night
        - Mara Serena Safari Lodge: High (Jul-Oct, late Dec/early Jan) ~$800-900+ USD double room/night; Low (Apr-Jun, Nov-mid Dec) ~$375-500+ USD double room/night

        Maasai Mara Budget Options:
        - Enchoro Wildlife Camp: High (Jul 1-Oct 31, Dec 22-Jan 5) $85 USD per person per night; Low (Apr 1-Jun 30) $65 USD per person per night; Shoulder (Jan 6-Mar 31, Nov 1-Dec 21) $75 USD per person per night
        - Masai Mara Manyatta Camp: High (Jul-Oct) $120 USD per person per night; Low (Apr-Jun) $90 USD per person per night; Mid (Jan-Mar, Nov-Dec) $100 USD per person per night
        - Oldarpoi Mara Camp: High (Jul 1-Oct 31, Dec 21-Jan 5) $100 USD per person per night; Low (Apr 1-Jun 30) $70 USD per person per night; Mid (Jan 6-Mar 31, Nov 1-Dec 20) $80 USD per person per night

        Amboseli Options:
        - Amboseli Serena Safari Lodge: High (Jul-Oct, late Dec/early Jan, Easter) ~$500-700+ USD double room/night; Low (Apr-Jun) ~$350-500+ USD double room/night
        - Elewana Tortilis Camp: High (Jun 1-Oct 31, Dec 21-Jan 5) $1,037 USD per person per night; Mid (Jan 6-Mar 31, Nov 1-Dec 20) $791 USD per person per night; Green/Low (Apr 1-May 31) $659 USD per person per night
        - Kibo Safari Camp: High (Jul 1-Oct 31, Dec 23-Jan 2) $190 USD per person per night; Low (Apr 1-Jun 30) $150 USD per person per night; Shoulder (Jan 3-Mar 31, Nov 1-Dec 22) $170 USD per person per night

        Tsavo Options:
        - Kilaguni Serena Safari Lodge: High (Jul-Oct, late Dec/early Jan, Easter) ~$450-650+ USD double room/night; Low (Apr-Jun) ~$300-450+ USD double room/night
        - Voi Wildlife Lodge: High (Jul-Oct, Dec 22-Jan 2, Easter) $150 USD per person per night; Low (Apr-Jun) $100 USD per person per night; Shoulder (Jan 3-Mar 31, Nov 1-Dec 21) $110 USD per person per night

        Lake Naivasha/Nakuru Options:
        - The Cliff Nakuru: High (Jul 1-Oct 31, Dec 21-Jan 5, Easter) $1,100 USD double tent/night; Mid (Jan 6-Mar 31, Jun 1-30, Nov 1-Dec 20) $990 USD double tent/night; Low (Apr 1-May 31) $880 USD double tent/night
        - Sarova Lion Hill Game Lodge: High (Jul-Oct, late Dec/early Jan, Easter) ~$450-650+ USD double room/night; Low (Apr-Jun) ~$350-500+ USD double room/night
        - Lake Naivasha Sopa Resort: High (Jul 1-Oct 31) $230 USD per person per night; Low (Apr 1-Jun 30) $140 USD per person per night; Shoulder (Jan 3-Mar 31, Nov 1-Dec 22) $165 USD per person per night; Peak (Dec 23-Jan 2) $260 USD per person per night

        Nairobi Options:
        - Giraffe Manor: High (Jul-Oct, Dec-Feb) ~$1,000 - $1,500+ USD per person per night; Low (Apr-May) ~$800 - $1,200+ USD per person per night
        - Hemingways Nairobi: ~$600 - $1,000+ USD per suite/night (less seasonal variation)
        - Sarova Stanley Hotel: ~$180 - $350+ USD double room/night (less seasonal variation)

        
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
            
            # Generate itinerary
            logger.info("Generating itinerary using Bedrock")
            itinerary = generate_itinerary(prompt)
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