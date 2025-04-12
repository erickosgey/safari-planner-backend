import os

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Change this to your Bedrock-enabled region
AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')

# Bedrock Configuration
BEDROCK_REGION = AWS_REGION  # Region for Bedrock service
BEDROCK_MODEL_ID = 'anthropic.claude-3-sonnet-20240229-v1:0'
BEDROCK_MAX_TOKENS = 3000
BEDROCK_TEMPERATURE = 1.0
BEDROCK_TOP_P = 0.999
BEDROCK_TOP_K = 50
BEDROCK_ANTHROPIC_VERSION = "bedrock-2023-05-31" 