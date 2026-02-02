
import sys
import boto3
import os
from botocore.exceptions import ClientError

# Ensure app path is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings

def reset_user(email: str):
    """
    Delete user from Users table and OTP table to reset registration state.
    """
    print(f"🔒 Resetting data for user: {email}")
    session = boto3.Session(region_name=settings.AWS_REGION)
    dynamodb = session.resource('dynamodb')
    
    # 1. Delete from Users Table
    users_table = dynamodb.Table(settings.DYNAMODB_USERS_TABLE)
    try:
        users_table.delete_item(Key={'email': email})
        print(f"✅ Deleted from {settings.DYNAMODB_USERS_TABLE}")
    except ClientError as e:
        print(f"❌ Error deleting from Users table: {e}")

    # 2. Delete from OTP Table
    otp_table = dynamodb.Table(settings.DYNAMODB_OTP_TABLE)
    try:
        otp_table.delete_item(Key={'email': email})
        print(f"✅ Deleted from {settings.DYNAMODB_OTP_TABLE}")
    except ClientError as e:
        print(f"❌ Error deleting from OTP table: {e}")

    # 3. Optional: Delete from Channel Mapping (if you had a dedicated table/index)
    # The current implementation creates a complex mapping, but usually it's stored 
    # within the user record or a separate table.
    # Checking TelegramAuthService... it uses ChannelMappingRepository.
    # Let's inspect ChannelMappingRepository to see where it stores data.
    
    print("\n⚠️  Note: If you need to clear the Telegram ID link completely, make sure ChannelMappings are also cleared.")
    print("For now, deleting the User record usually breaks the link effectively for the app logic.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/reset_user.py <email>")
        sys.exit(1)
    
    email_to_reset = sys.argv[1]
    reset_user(email_to_reset)
