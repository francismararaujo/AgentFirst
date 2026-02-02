import boto3
import os

def test():
    print("Listing Tables...")
    
    regions = ['us-east-1', 'sa-east-1', 'us-west-2']
    
    for reg in regions:
        print(f"\n--- Region: {reg} ---")
        try:
            dynamodb = boto3.client('dynamodb', region_name=reg)
            response = dynamodb.list_tables()
            print("Tables:", response.get('TableNames'))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test()
