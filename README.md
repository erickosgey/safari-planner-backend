# Safari Planner API

This is an AWS Lambda function that provides an API for safari planning requests.

## Setup and Deployment

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a deployment package:
```bash
zip -r deployment.zip src/ requirements.txt
```

3. Deploy to AWS Lambda:
- Create a new Lambda function in the AWS Console
- Upload the deployment.zip file
- Set the handler to `lambda_function.lambda_handler`
- Set the runtime to Python 3.9 or later
- Configure an API Gateway trigger

## API Usage

Send a POST request to your API Gateway endpoint with the following JSON structure:

```json
{
  "travelDates": {
    "startDate": "2025-12-20",
    "endDate": "2025-12-27",
    "isFlexible": true
  },
  "group": {
    "international": {
      "adults": 2,
      "children": 1
    },
    "resident": {
      "adults": 0,
      "children": 0
    }
  },
  "accommodation": "Mid-range Lodge",
  "interests": [
    "Big Five wildlife sightings",
    "Photography",
    "Family-friendly"
  ],
  "travelStyle": "Some structure, some free time",
  "email": "user@example.com",
  "specialRequests": "We're celebrating a birthday and would love a surprise cake in the bush!"
}
```

The API will validate the input and return the same structure if valid, or an error message if invalid.

## Development

To test locally, you can use the AWS SAM CLI or create a simple test script that calls the lambda_handler function directly. 