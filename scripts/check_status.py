import asyncio
import logging
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_status():
    print("\n--- iFood Store Status Diagnostic ---")
    
    secrets = SecretsManager()
    connector = iFoodConnector(secrets_manager=secrets)
    
    # Authenticate
    if not await connector.authenticate():
        print("❌ Authentication Failed")
        return
        
    # OVERRIDE Merchant ID with correct UUID (from logs)
    # The Short ID (3195051) fails on v1.0 API
    if connector.credentials:
        print(f"DEBUG: Replacing Short ID {connector.credentials.merchant_id} with UUID")
        connector.credentials.merchant_id = "2828a12d-bb09-4104-95c9-659f445c438f"

    # 1. Check Merchant Status
    print("\n1. Checking Merchant Status...")
    try:
        status = await connector.get_merchant_status()
        print(f"Status Object: {status}")
        # Assuming MerchantStatus has attributes or is a dict
        if hasattr(status, '__dict__'):
            print(f"Details: {status.__dict__}")
    except Exception as e:
        print(f"❌ Error getting status: {e}")

    # 2. Check Interruptions (Interruptions API)
    print("\n2. Checking Active Interruptions...")
    try:
        interruptions = await connector.list_interruptions()
        if interruptions:
            print(f"⚠️ Found {len(interruptions)} active interruptions:")
            print(json.dumps(interruptions, indent=2))
        else:
            print("✅ No active interruptions found.")
    except Exception as e:
        print(f"❌ Error getting interruptions: {e}")
        
    # 3. Check Store Status (General)
    print("\n3. Checking General Store Status...")
    try:
        store_status = await connector.get_store_status()
        print(f"Store Status: {store_status}")
    except Exception as e:
        print(f"❌ Error getting store status: {e}")

    # 4. Check Polling (Heartbeat Simulation)
    print("\n4. Checking Polling (Heartbeat)...")
    try:
        events = await connector.poll_orders()
        print(f"✅ Polling successful! Received {len(events)} events.")
        if events:
            print("Event IDs:", [e.id for e in events])
    except Exception as e:
        print(f"❌ Error polling events: {e}")


if __name__ == "__main__":
    asyncio.run(check_status())
