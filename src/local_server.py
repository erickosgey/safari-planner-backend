from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import boto3
from lambda_function import lambda_handler
from config import AWS_REGION, AWS_PROFILE

app = FastAPI(title="Safari Planner API")

# Configure AWS Session
boto3.setup_default_session(profile_name=AWS_PROFILE, region_name=AWS_REGION)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/safari-planner")
async def safari_planner(request: Request):
    # Get the raw request body
    body = await request.json()
    
    # Call the Lambda handler with the request body
    response = lambda_handler(body, None)
    
    # Parse the response body if it's a string
    if isinstance(response.get("body"), str):
        response["body"] = json.loads(response["body"])
    
    # Return the response with the correct status code
    return response["body"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 