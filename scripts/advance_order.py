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

async def advance_order(order_id):
    print(f"--- Advancing Order {order_id} ---")
    secrets = SecretsManager()
    connector = iFoodConnector(secrets_manager=secrets)
    
    if not await connector.authenticate():
        print("Auth failed")
        return

    # Override merchant_id to be safe
    if connector.credentials:
        connector.credentials.merchant_id = "2828a12d-bb09-4104-95c9-659f445c438f"

    try:
        # 1. Start Preparation
        print("\n1. Start Preparation...")
        if hasattr(connector, 'start_preparation'):
            res = await connector.start_preparation(order_id)
            print(res)
        else:
            print("Method start_preparation not found!")

        # Wait a bit
        await asyncio.sleep(2)

        # 2. Ready To Pickup (Usually required before Dispatch for Own Delivery)
        print("\n2. Ready To Pickup...")
        if hasattr(connector, 'ready_to_pickup'):
            res = await connector.ready_to_pickup(order_id)
            print(res)
        else:
            print("Method ready_to_pickup not found!")

        # Wait a bit
        await asyncio.sleep(2)

        # 3. Dispatch
        print("\n3. Dispatch...")
        res = await connector.dispatch_order(order_id)
        print(res)
        
    except Exception as e:
        print(f"Error advancing order: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("order_id", help="The iFood Order ID")
    args = parser.parse_args()
    
    asyncio.run(advance_order(args.order_id))
