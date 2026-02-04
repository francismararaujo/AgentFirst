
import os
import sys
import json
import asyncio
from unittest.mock import MagicMock, patch

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set dummy environment variables to avoid validation errors
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["DYNAMODB_USERS_TABLE"] = "agentfirst-users-development"
os.environ["SNS_OMNICHANNEL_TOPIC_ARN"] = "arn:aws:sns:us-east-1:123456789012:omnichannel-topic"
os.environ["LOG_LEVEL"] = "DEBUG"

# Mock AWS services to facilitate local testing without credentials
with patch('boto3.client') as mock_boto, \
     patch('boto3.resource') as mock_resource:
    
    # Mock DynamoDB Table
    mock_table = MagicMock()
    mock_resource.return_value.Table.return_value = mock_table
    
    # Mock Secrets Manager
    mock_secrets = MagicMock()
    mock_boto.return_value.get_secret_value.return_value = {
        'SecretString': json.dumps({'telegram_bot_token': '123456:ABC'})
    }
    
    # Mock Bedrock
    mock_bedrock = MagicMock()
    
    from app.main import telegram_webhook
    from fastapi import Request

    async def run_debug():
        print("--- STARTING DEBUG ---")
        
        # Payload simulando uma mensagem do Telegram
        payload = {
            "update_id": 10000,
            "message": {
                "date": 1441645532,
                "chat": {
                    "last_name": "Test",
                    "id": 1111111,
                    "type": "private",
                    "first_name": "Test",
                    "username": "Test"
                },
                "message_id": 1365,
                "from": {
                    "last_name": "Test",
                    "id": 1111111,
                    "first_name": "Test",
                    "username": "Test"
                },
                "text": "Teste de debug local"
            }
        }
        
        # Criar mock do Request
        scope = {"type": "http"}
        request = Request(scope)
        request._body = json.dumps(payload).encode('utf-8')
        
        try:
            print("Invoking webhook endpoint...")
            # Chamada direta à função assíncrona
            await telegram_webhook(request)
            print("Webhook executed successfully (check logs above if any)")
            
        except Exception as e:
            print(f"\n!!! EXCEPTION CAUGHT !!!")
            print(f"Type: {type(e)}")
            print(f"Message: {e}")
            import traceback
            traceback.print_exc()

    if __name__ == "__main__":
        asyncio.run(run_debug())
