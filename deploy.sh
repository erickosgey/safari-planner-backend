#!/bin/bash

# Check if AWS SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "AWS SAM CLI is not installed. Please install it first."
    echo "Visit: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

# Build the deployment package
echo "Building deployment package..."
sam build

# Deploy the application
echo "Deploying application..."
sam deploy --guided

echo "Deployment complete!" 