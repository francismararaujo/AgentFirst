import asyncio
import logging
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def list_orders():
    print("--- Listing Orders ---")
    secrets = SecretsManager()
    connector = iFoodConnector(secrets_manager=secrets)
    
    if not await connector.authenticate():
        print("Auth failed")
        return

    # Override merchant_id to be safe (same fix as before)
    if connector.credentials:
        connector.credentials.merchant_id = "2828a12d-bb09-4104-95c9-659f445c438f"

    try:
        # Attempt to list orders (undocumented or common endpoint)
        print("Requesting GET /order/v1.0/orders ...")
        # Note: headers usually needed?
        response = await connector._make_request('GET', '/order/v1.0/orders')
        
        print("\nExisting Orders:")
        print(json.dumps(response, indent=2))
        
        # If response implies filtering:
        # Some APIs require ?status=PLACED
        
    except Exception as e:
        print(f"Error listing orders: {e}")

if __name__ == "__main__":
    asyncio.run(list_orders())
