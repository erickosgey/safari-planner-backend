import os

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Change this to your Bedrock-enabled region
AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')

# Bedrock Configuration
BEDROCK_MODEL_ID = 'deepseek.deepseek-ai-7b'
BEDROCK_MAX_TOKENS = 4096
BEDROCK_TEMPERATURE = 0.7
BEDROCK_TOP_P = 0.9 