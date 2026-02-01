import asyncio
import logging
import sys
import os
import boto3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dynamo():
    print(f"--- Testing DynamoDB Access ---")
    print(f"Region: {settings.AWS_REGION}")
    print(f"Table: {settings.DYNAMODB_USERS_TABLE}")
    
    try:
        dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
        table = dynamodb.Table(settings.DYNAMODB_USERS_TABLE)
        
        # Try a simple scan (limit 1) or get_item
        print("Scanning 1 item...")
        response = table.scan(Limit=1)
        print("Scan result items:", response.get('Items'))
        print("✅ DynamoDB Access OK!")
        
    except Exception as e:
        print(f"❌ Error access DynamoDB: {e}")

if __name__ == "__main__":
    asyncio.run(test_dynamo())
