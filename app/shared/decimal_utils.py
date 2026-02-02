import json
from decimal import Decimal

def to_decimal(obj):
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_decimal(v) for v in obj]
    return obj
