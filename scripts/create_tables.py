import boto3
import time
import sys

TABLES = [
    {
        "TableName": "agentfirst-otp",
        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "email", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "Enabled": True,
            "AttributeName": "expires_at"
        }
    },
    {
        "TableName": "agentfirst-users",
        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "email", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST"
    },
    {
        "TableName": "agentfirst-sessions",
        "KeySchema": [
            {"AttributeName": "email", "KeyType": "HASH"},
            {"AttributeName": "session_id", "KeyType": "RANGE"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "session_id", "AttributeType": "S"}
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "Enabled": True,
            "AttributeName": "ttl"
        }
    },
    {
        "TableName": "agentfirst-memory",
        "KeySchema": [
            {"AttributeName": "email", "KeyType": "HASH"},
            {"AttributeName": "domain", "KeyType": "RANGE"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "domain", "AttributeType": "S"}
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "Enabled": True,
            "AttributeName": "ttl"
        }
    },
    {
        "TableName": "agentfirst-usage",
        "KeySchema": [
            {"AttributeName": "email", "KeyType": "HASH"},
            {"AttributeName": "month", "KeyType": "RANGE"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "month", "AttributeType": "S"}
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "Enabled": True,
            "AttributeName": "ttl"
        }
    },
    {
        "TableName": "agentfirst-audit-logs",
        "KeySchema": [
            {"AttributeName": "email", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
            {"AttributeName": "agent", "AttributeType": "S"}
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "agent-index",
                "KeySchema": [
                    {"AttributeName": "agent", "KeyType": "HASH"},
                    {"AttributeName": "timestamp", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "Enabled": True,
            "AttributeName": "ttl"
        }
    },
    {
        "TableName": "agentfirst-escalation",
        "KeySchema": [
            {"AttributeName": "escalation_id", "KeyType": "HASH"}
        ],
        "AttributeDefinitions": [
            {"AttributeName": "escalation_id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"}
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "user-index",
                "KeySchema": [
                    {"AttributeName": "email", "KeyType": "HASH"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {
            "Enabled": True,
            "AttributeName": "ttl"
        }
    }
]

def create_tables():
    print("--- Creating Tables in us-east-1 ---")
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
    for table_def in TABLES:
        name = table_def["TableName"]
        print(f"Checking {name}...")
        try:
            dynamodb.describe_table(TableName=name)
            print(f"  Exists.")
        except dynamodb.exceptions.ResourceNotFoundException:
            print(f"  Creating {name}...")
            ttl_spec = table_def.pop("TimeToLiveSpecification", None)
            
            dynamodb.create_table(**table_def)
            print(f"  Created request sent.")
            
            if ttl_spec:
                print(f"  Enabling TTL (waiting for table active)...")
                # Wait for active
                waiter = dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=name)
                
                dynamodb.update_time_to_live(
                    TableName=name,
                    TimeToLiveSpecification=ttl_spec
                )
                print("  TTL Enabled.")
                
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    create_tables()
