import asyncio
import logging
import sys
import os
import urllib.request
import urllib.parse
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config.secrets_manager import SecretsManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NGROK_URL = "https://f4500dee5e2d.ngrok-free.app"

async def setup_webhook():
    print("--- Setting up Telegram Webhook ---")
    secrets = SecretsManager()
    token = secrets.get_telegram_token()
    
    if not token:
        print("❌ Telegram Token not found in Secrets Manager")
        return

    webhook_url = f"{NGROK_URL}/webhook/telegram"
    print(f"Target URL: {webhook_url}")
    
    api_url = f"https://api.telegram.org/bot{token}/setWebhook"
    data = urllib.parse.urlencode({'url': webhook_url}).encode()
    
    try:
        req = urllib.request.Request(api_url, data=data)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print("\nResult:")
            print(result)
            if result.get('ok'):
                print("\n✅ Webhook Configured Successfully!")
            else:
                print("\n❌ Failed to configure webhook")
                    
    except Exception as e:
        print(f"Error: {e}")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Setup Telegram Webhook')
    parser.add_argument('--url', help='Webhook URL')
    args = parser.parse_args()

    if args.url:
        NGROK_URL = args.url.replace('/webhook/telegram', '')
        print(f"Using provided URL: {NGROK_URL}")
    
    asyncio.run(setup_webhook())
