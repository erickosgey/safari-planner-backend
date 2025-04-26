import os

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Change this to your Bedrock-enabled region
AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')

# Bedrock Configuration
BEDROCK_REGION = AWS_REGION
BEDROCK_MODEL_ID = 'anthropic.claude-3-sonnet-20240229-v1:0'
BEDROCK_MAX_TOKENS = 3000  
BEDROCK_TEMPERATURE = 0.1  
BEDROCK_TOP_P = 0.9      
BEDROCK_TOP_K = 20       
BEDROCK_ANTHROPIC_VERSION = "bedrock-2023-05-31"
