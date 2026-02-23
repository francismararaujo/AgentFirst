class EcommerceUpdaterAgent:
    def __init__(self):
        self.descriptor = {
            "name": "OmnichannelUpdater",
            "domain": "ECOMMERCE_CHANNELS"
        }

    def push_to_platforms(self, sync_payload, gatekeeper):
        # BEFORE pushing to platforms, the Agent MUST pass the payload through the Gatekeeper
        print(f"🛒 [OmnichannelUpdater] Preparing to push {len(sync_payload)} item updates to iFood and Shopee.")
        
        if not gatekeeper.validate_action(self.descriptor, "update_platform_stock", payload=sync_payload):
            print("🛒 [OmnichannelUpdater] 🔴 Operation aborted by AgentFirst Core.")
            return False
            
        # The actual simulated external API call
        print("🛒 [OmnichannelUpdater] 🟢 Calling external APIs...")
        for item in sync_payload:
            print(f"   📍 -> iFood API: Updated SKU {item['sku']} | Price: R${item['new_price']:.2f} | Stock: {item['new_stock']}")
            print(f"   📍 -> Shopee API: Updated SKU {item['sku']} | Price: R${item['new_price']:.2f} | Stock: {item['new_stock']}")
            
        print("🛒 [OmnichannelUpdater] ✅ All platforms synced successfully.")
        return True
