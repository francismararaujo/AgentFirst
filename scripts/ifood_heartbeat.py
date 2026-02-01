import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_heartbeat():
    logger.info("Starting iFood Polling Heartbeat to keep store OPEN...")
    
    secrets = SecretsManager()
    connector = iFoodConnector(secrets_manager=secrets)
    
    # Authenticate first
    if not await connector.authenticate():
        logger.error("Failed to authenticate with iFood")
        return

    while True:
        try:
            logger.info("Sending heartbeat (polling)...")
            
            # This method calls /polling endpoint which acts as heartbeat
            events = await connector.poll_orders()
            
            if events:
                logger.info(f"Received {len(events)} events during heartbeat")
                # Important: Acknowledge events to clear queue
                await connector.acknowledge_events(events)
            else:
                logger.info("Heartbeat OK (No events)")
                
        except Exception as e:
            logger.error(f"Error in heartbeat: {str(e)}")
            # Try to re-authenticate on error
            await connector.authenticate()
            
        # Wait 30 seconds (Mandatory interval)
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(run_heartbeat())
    except KeyboardInterrupt:
        logger.info("Stopping heartbeat...")
