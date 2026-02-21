import os

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Change this to your Bedrock-enabled region
AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')

# Bedrock Configuration
BEDROCK_REGION = AWS_REGION
BEDROCK_MODEL_ID = 'anthropic.claude-3-5-haiku-20241022-v1:0'
BEDROCK_INFERENCE_PROFILE = 'arn:aws:bedrock:us-east-1:488210324868:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0'
BEDROCK_MAX_TOKENS = 3000  
BEDROCK_TEMPERATURE = 0.1  
BEDROCK_TOP_P = 0.9      
BEDROCK_TOP_K = 20       
BEDROCK_ANTHROPIC_VERSION = "bedrock-2023-05-31"
