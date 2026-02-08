
import boto3
import json
import os
from botocore.exceptions import ClientError

def get_secret(secret_name, region_name="us-east-1"):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        print(f"Error retrieving {secret_name}: {e}")
        return None

    if 'SecretString' in get_secret_value_response:
        return json.loads(get_secret_value_response['SecretString'])
    return None

def main():
    print("Fetching secrets from AWS...")
    
    env_content = []
    
    # 1. iFood Credentials
    print("Fetching iFood credentials...")
    ifood_creds = get_secret("AgentFirst/ifood-credentials")
    if not ifood_creds:
        ifood_creds = get_secret("ifood-oauth-credentials")
        
    if ifood_creds:
        env_content.append(f"IFOOD_CLIENT_ID={ifood_creds.get('client_id', '')}")
        env_content.append(f"IFOOD_CLIENT_SECRET={ifood_creds.get('client_secret', '')}")
        env_content.append(f"IFOOD_MERCHANT_ID={ifood_creds.get('merchant_id', '')}")
        env_content.append(f"IFOOD_WEBHOOK_SECRET={ifood_creds.get('webhook_secret', '')}")
        print("Found iFood credentials.")
    else:
        print("WARNING: Could not find iFood credentials.")

    # 2. Telegram Credentials
    print("Fetching Telegram credentials...")
    telegram_creds = get_secret("AgentFirst/telegram-bot-token")
    if telegram_creds:
        env_content.append(f"TELEGRAM_BOT_TOKEN={telegram_creds.get('bot_token', '')}")
        env_content.append(f"TELEGRAM_CHAT_ID={telegram_creds.get('chat_id', '')}")
        print("Found Telegram credentials.")
    else:
        print("WARNING: Could not find Telegram credentials.")

    # Write to .env
    env_path = ".env"
    with open(env_path, "w") as f:
        f.write("\n".join(env_content))
        f.write("\n")
        f.write("LIVE_TEST=true\n") # Enable live tests automatically
    
    print(f"Successfully wrote secrets to {env_path}")

if __name__ == "__main__":
    main()
