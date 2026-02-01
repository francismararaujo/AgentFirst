import asyncio
import logging
import sys
import os
import json
from dataclasses import asdict

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def peek_orders():
    print("--- Peeking iFood Event Queue (No ACK) ---")
    
    secrets = SecretsManager()
    connector = iFoodConnector(secrets_manager=secrets)
    
    # Authenticate
    if not await connector.authenticate():
        print("❌ Failed to authenticate with iFood")
        return

    try:
        print("🔍 Polling events...")
        events = await connector.poll_orders()
        
        if events:
            print(f"✅ Found {len(events)} events!")
            for event in events:
                # Fix: Convert dataclass to dict for JSON serialization
                print(json.dumps(asdict(event), indent=2, default=str))
            
            print("\n⚠️ Events were NOT acknowledged. They should still be delivered to Webhook.")
        else:
            print("📭 No events found in queue.")
            
    except Exception as e:
        print(f"❌ Error polling: {e}")

if __name__ == "__main__":
    asyncio.run(peek_orders())
