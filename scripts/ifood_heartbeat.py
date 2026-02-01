"""iFood Multi-Tenant Polling Heartbeat Service

This script continuously polls iFood for ALL active merchants in the system.
It runs as an ECS Fargate task and keeps all customer stores open and available.

Architecture:
- Centralized credentials (AgentFirst has ONE set of iFood API credentials)
- Dynamic merchant_id per customer (stored in DynamoDB)
- Loops through all active merchants every 30 seconds
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager
from app.repositories.merchant_repository import MerchantRepository

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def poll_merchant(
    merchant: Dict[str, Any],
    secrets_manager: SecretsManager,
    merchant_repo: MerchantRepository
) -> None:
    """
    Poll a single merchant's iFood store
    
    Args:
        merchant: Merchant data from DynamoDB
        secrets_manager: Secrets manager instance
        merchant_repo: Merchant repository for status updates
    """
    merchant_id = merchant['merchant_id']
    user_email = merchant['user_email']
    
    try:
        # Create connector with centralized credentials + dynamic merchant_id
        connector = iFoodConnector(
            secrets_manager=secrets_manager,
            merchant_id=merchant_id
        )
        
        # Authenticate
        if not await connector.authenticate():
            error_msg = "Authentication failed"
            logger.error(f"[{merchant_id}] {error_msg}")
            merchant_repo.update_poll_status(merchant_id, user_email, success=False, error=error_msg)
            return
        
        # Poll for orders/events
        events = await connector.poll_orders()
        
        if events:
            logger.info(f"[{merchant_id}] Received {len(events)} events")
            # Acknowledge events to clear queue
            await connector.acknowledge_events(events)
        else:
            logger.info(f"[{merchant_id}] Heartbeat OK (No events)")
        
        # Update success status
        merchant_repo.update_poll_status(merchant_id, user_email, success=True)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{merchant_id}] Polling failed: {error_msg}", exc_info=True)
        merchant_repo.update_poll_status(merchant_id, user_email, success=False, error=error_msg)


async def run_heartbeat():
    """
    Main polling loop for all active merchants
    
    Continuously polls all active merchants every 30 seconds.
    Each merchant is polled sequentially to avoid rate limiting.
    """
    logger.info("🚀 Starting Multi-Tenant iFood Polling Heartbeat...")
    
    secrets_manager = SecretsManager()
    merchant_repo = MerchantRepository()
    
    while True:
        try:
            # Get all active merchants from DynamoDB
            merchants = merchant_repo.get_active_merchants()
            
            if not merchants:
                logger.warning("⚠️  No active merchants found. Waiting...")
            else:
                logger.info(f"📊 Polling {len(merchants)} active merchant(s)...")
                
                # Poll each merchant sequentially
                for merchant in merchants:
                    await poll_merchant(merchant, secrets_manager, merchant_repo)
                
                logger.info(f"✅ Completed polling cycle for {len(merchants)} merchant(s)")
            
        except Exception as e:
            logger.error(f"❌ Error in polling cycle: {str(e)}", exc_info=True)
        
        # Wait 30 seconds before next cycle (iFood requirement)
        logger.info("⏳ Waiting 30 seconds before next cycle...")
        await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(run_heartbeat())
    except KeyboardInterrupt:
        logger.info("🛑 Stopping heartbeat service...")
