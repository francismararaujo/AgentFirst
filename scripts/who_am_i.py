import asyncio
import logging
import sys
import os
import urllib.request
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.secrets_manager import SecretsManager

async def who_am_i():
    print("--- Verifying Bot Identity ---")
    secrets = SecretsManager()
    token = secrets.get_telegram_token()
    
    if not token:
        print("❌ Telegram Token not found in Secrets Manager")
        return

    api_url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        with urllib.request.urlopen(api_url) as response:
            result = json.loads(response.read().decode())
            if result.get('ok'):
                user = result['result']
                print(f"✅ Bot Information:")
                print(f"   ID: {user['id']}")
                print(f"   Name: {user['first_name']}")
                print(f"   Username: @{user['username']}")
            else:
                print(f"❌ Failed to get bot info: {result}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(who_am_i())
