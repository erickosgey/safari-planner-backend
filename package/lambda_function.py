import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime
import boto3
import json
from config import BEDROCK_MODEL_ID, BEDROCK_MAX_TOKENS, BEDROCK_TEMPERATURE, BEDROCK_TOP_P

class TravelDates(BaseModel):
    startDate: date
    endDate: date
    isFlexible: bool

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

def generate_prompt(request_data: SafariRequest) -> str:
    # Calculate total number of days
    start_date = datetime.strptime(str(request_data.travelDates.startDate), "%Y-%m-%d")
    end_date = datetime.strptime(str(request_data.travelDates.endDate), "%Y-%m-%d")
    total_days = (end_date - start_date).days + 1
    
    total_guests = (
        request_data.group.international.adults + 
        request_data.group.international.children +
        request_data.group.resident.adults + 
        request_data.group.resident.children
    )
    
    has_children = (
        request_data.group.international.children > 0 or 
        request_data.group.resident.children > 0
    )

    # Create a more structured prompt for DeepSeek
    prompt = f"""Task: Create a detailed safari itinerary for Kenya.

Input Parameters:
- Trip Duration: {total_days} days
- Travel Dates: {request_data.travelDates.startDate} to {request_data.travelDates.endDate}
- Group Composition: {total_guests} people ({'including children' if has_children else 'adults only'})
- Accommodation Preference: {request_data.accommodation}
- Special Interests: {', '.join(request_data.interests)}
- Travel Style: {request_data.travelStyle}
- Special Requirements: {request_data.specialRequests}

Requirements:
1. Create a day-by-day itinerary with specific activities
2. Include appropriate activities for children if present
3. Focus on the requested interests
4. Match the preferred travel style
5. Suggest suitable accommodations
6. Include wildlife viewing opportunities
7. Plan meal arrangements
8. Consider travel times between locations
9. Include photography opportunities if requested
10. Address special requests

Output Format:
Please provide the response in the following JSON structure:
{{
    "itinerary": {{
        "overview": "Brief summary of the safari",
        "days": [
            {{
                "day": 1,
                "date": "YYYY-MM-DD",
                "location": "Name of the area/park",
                "accommodation": "Name of lodge/camp",
                "meals": ["breakfast", "lunch", "dinner"],
                "activities": [
                    {{
                        "time": "Approximate time",
                        "description": "Detailed description",
                        "duration": "Duration in hours",
                        "suitable_for_children": true/false
                    }}
                ],
                "highlights": ["Key highlights of the day"]
            }}
        ]
    }},
    "special_notes": ["Any special considerations or notes"],
    "photography_tips": ["Photography tips if relevant"],
    "packing_suggestions": ["Relevant packing suggestions"]
}}

Please ensure the itinerary is realistic and suitable for the specified group composition and preferences."""

    return prompt

def generate_itinerary(prompt: str) -> Dict:
    # Initialize the Bedrock client
    bedrock = boto3.client('bedrock-runtime')
    
    # Call DeepSeek model through Bedrock
    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps({
            "prompt": prompt,
            "max_tokens": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
            "top_p": BEDROCK_TOP_P,
        })
    )
    
    # Parse the response
    response_body = json.loads(response['body'].read())
    # Extract the generated text and parse it as JSON
    generated_text = response_body['completion']
    try:
        # Find the JSON content within the response
        json_start = generated_text.find('{')
        json_end = generated_text.rfind('}') + 1
        itinerary_json = json.loads(generated_text[json_start:json_end])
        return itinerary_json
    except json.JSONDecodeError:
        return {"error": "Failed to generate valid itinerary"}

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # Parse and validate the input
        request_data = SafariRequest(**event)
        
        # Generate the prompt
        prompt = generate_prompt(request_data)
        
        # Generate the itinerary using Bedrock
        itinerary = generate_itinerary(prompt)
        
        # Combine the original request with the generated itinerary
        response_data = {
            "request": request_data.model_dump(),
            "itinerary": itinerary
        }
        
        return {
            "statusCode": 200,
            "body": json.dumps(response_data, default=str),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        } 