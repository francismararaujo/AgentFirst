import asyncio
import logging
import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def dispatch_order(order_id):
    print(f"--- Dispatching Order {order_id} ---")
    secrets = SecretsManager()
    connector = iFoodConnector(secrets_manager=secrets)
    
    if not await connector.authenticate():
        print("Auth failed")
        return

    # Override merchant_id to be safe
    if connector.credentials:
        connector.credentials.merchant_id = "2828a12d-bb09-4104-95c9-659f445c438f"

    try:
        print(f"Calling dispatch_order({order_id})...")
        result = await connector.dispatch_order(order_id)
        print("\nResult:")
        print(result)
        
    except Exception as e:
        print(f"Error dispatching order: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("order_id", help="The iFood Order ID (UUID or Short ID)")
    args = parser.parse_args()
    
    asyncio.run(dispatch_order(args.order_id))
