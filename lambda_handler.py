"""Lambda handler entry point for AgentFirst2 MVP

This module serves as the entry point for AWS Lambda.
It imports and delegates to the main handler in app/main.py
"""

import sys
import asyncio
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point
    
    This function handles both sync and async operations by:
    1. Importing the main handler from app/
    2. Using Mangum to bridge API Gateway events to FastAPI
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    try:
        # Import the main handler
        from app.main import app
        from mangum import Mangum
        
        # Create Mangum handler
        # lifespan="off" to allow faster cold starts and avoid some async issues
        handler = Mangum(app, lifespan="off")
        
        # Call handler
        result = handler(event, context)
        
        # Check if result is a coroutine (async function) - generic safety
        if asyncio.iscoroutine(result):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(result)
            finally:
                loop.close()
        
        return result
        
    except Exception as e:
        # Fallback error handling
        print(f"CRITICAL ERROR in lambda_handler: {e}", flush=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": "An unexpected error occurred."
            }),
            "headers": {"Content-Type": "application/json"}
        }