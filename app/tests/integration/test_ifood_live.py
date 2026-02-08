
import pytest
import asyncio
import os
from datetime import datetime
from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager
from dotenv import load_dotenv

load_dotenv()

# Only run if explicitly requested via environment variable to avoid hitting real API in CI/CD
# Usage: LIVE_TEST=true pytest tests/integration/test_ifood_live.py
run_live = os.getenv("LIVE_TEST") == "true"

@pytest.mark.skipif(not run_live, reason="Skipping live API tests. Run with LIVE_TEST=true")
class TestiFoodLiveIntegration:
    """
    LIVE Integration Tests for iFood Connector.
    WARNING: This hits the REAL iFood API. Ensure you are using a Test/Sandbox Merchant if possible.
    """
    
    @pytest.fixture
    def connector(self):
        secrets_manager = SecretsManager()
        return iFoodConnector(secrets_manager)

    @pytest.mark.asyncio
    async def test_live_authentication(self, connector):
        """Test authentication with real credentials"""
        if not os.getenv("IFOOD_CLIENT_ID"):
             pytest.skip("Missing IFOOD_CLIENT_ID")
             
        print("\n🔐 Testing Live Authentication...")
        result = await connector.authenticate()
        assert result is True, "Authentication failed"
        assert connector.token is not None
        print("✅ Authentication Successful!")

    @pytest.mark.asyncio
    async def test_live_merchant_status(self, connector):
        """Test get merchant status from real API"""
        if not os.getenv("IFOOD_CLIENT_ID"):
             pytest.skip("Missing IFOOD_CLIENT_ID")

        print("\n🏪 Testing Live Merchant Status...")
        await connector.authenticate()
        status = await connector.get_merchant_status()
        
        assert status is not None
        print(f"Status payload: {status}")
        
        # iFood API returns list of operation statuses
        if isinstance(status, list):
            assert len(status) > 0
            main_status = status[0]
            assert 'available' in main_status or 'state' in main_status or 'operation' in main_status
        else:
            assert 'state' in status or 'available' in status
        print(f"✅ Merchant Status Check Passed")

    @pytest.mark.asyncio
    async def test_live_get_orders(self, connector):
        """Test get_orders from real API"""
        if not os.getenv("IFOOD_CLIENT_ID"):
             pytest.skip("Missing IFOOD_CLIENT_ID")

        print("\n📋 Testing Live get_orders()...")
        await connector.authenticate()
        # Attempt to fetch orders (might be empty)
        orders = await connector.get_orders()
        assert isinstance(orders, list)
        print(f"✅ Retrieved {len(orders)} orders successfully.")
