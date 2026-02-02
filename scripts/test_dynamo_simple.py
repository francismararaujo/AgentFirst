import boto3
import os

def test():
    print("Testing DynamoDB Simple...")
    try:
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('agentfirst-users')
        print(f"Table: {table.name}")
        print("Scannning...")
        # Now it should work and return empty list (or items)
        response = table.scan(Limit=1)
        print("Items:", response.get('Items'))
        print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test()
