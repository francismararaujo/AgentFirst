"""Migration Script: Add Current Merchant to DynamoDB

This script migrates the existing hardcoded merchant to the new multi-tenant
merchants table in DynamoDB.

Usage:
    python scripts/migrate_merchant.py --email YOUR_EMAIL
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.repositories.merchant_repository import MerchantRepository

# Current merchant (hardcoded in old system)
CURRENT_MERCHANT_ID = "2828a12d-bb09-4104-95c9-659f445c438f"


def migrate_merchant(user_email: str) -> bool:
    """
    Migrate current merchant to DynamoDB
    
    Args:
        user_email: Email of the merchant owner
        
    Returns:
        True if successful, False otherwise
    """
    print(f"🔄 Migrating merchant {CURRENT_MERCHANT_ID} to DynamoDB...")
    print(f"   Owner: {user_email}")
    
    merchant_repo = MerchantRepository()
    
    # Check if merchant already exists
    existing = merchant_repo.get_merchant(CURRENT_MERCHANT_ID, user_email)
    if existing:
        print(f"⚠️  Merchant already exists in DynamoDB!")
        print(f"   Status: {existing.get('status')}")
        print(f"   Polling: {existing.get('polling_enabled')}")
        return True
    
    # Create merchant entry
    success = merchant_repo.create_merchant({
        'merchant_id': CURRENT_MERCHANT_ID,
        'user_email': user_email,
        'platform': 'ifood',
        'status': 'active',
        'polling_enabled': True
    })
    
    if success:
        print(f"✅ Merchant migrated successfully!")
        print(f"   Merchant ID: {CURRENT_MERCHANT_ID}")
        print(f"   Platform: iFood")
        print(f"   Status: Active")
        print(f"   Polling: Enabled")
        print(f"\n🎉 Migration complete! The polling service will now include this merchant.")
        return True
    else:
        print(f"❌ Migration failed!")
        return False


def verify_migration(user_email: str) -> bool:
    """
    Verify that migration was successful
    
    Args:
        user_email: Email of the merchant owner
        
    Returns:
        True if merchant exists and is active, False otherwise
    """
    print(f"\n🔍 Verifying migration...")
    
    merchant_repo = MerchantRepository()
    merchant = merchant_repo.get_merchant(CURRENT_MERCHANT_ID, user_email)
    
    if not merchant:
        print(f"❌ Verification failed: Merchant not found!")
        return False
    
    print(f"✅ Verification successful!")
    print(f"   Merchant ID: {merchant['merchant_id']}")
    print(f"   User Email: {merchant['user_email']}")
    print(f"   Platform: {merchant['platform']}")
    print(f"   Status: {merchant['status']}")
    print(f"   Polling Enabled: {merchant['polling_enabled']}")
    print(f"   Created At: {datetime.fromtimestamp(merchant['created_at'])}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Migrate current merchant to DynamoDB')
    parser.add_argument(
        '--email',
        required=True,
        help='Email of the merchant owner'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify if merchant exists (do not migrate)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("iFood Merchant Migration Script")
    print("=" * 60)
    
    if args.verify_only:
        success = verify_migration(args.email)
    else:
        success = migrate_merchant(args.email)
        if success:
            verify_migration(args.email)
    
    print("=" * 60)
    
    if success:
        print("\n✅ All done! You can now:")
        print("   1. Check ECS logs to see multi-tenant polling")
        print("   2. Use API endpoints to manage merchants")
        print("   3. Add more merchants via API")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
