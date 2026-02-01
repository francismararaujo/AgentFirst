"""Lambda handler entry point for AgentFirst2 MVP

This module serves as the entry point for AWS Lambda.
It imports and delegates to the main handler in app/lambda_handler.py
"""

import sys
import asyncio
import json
import logging
import traceback
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point with HEAVY DEBUGGING
    """
    print("DEBUG: lambda_handler START", flush=True)
    try:
        print(f"DEBUG: Event keys: {list(event.keys())}", flush=True)
        
        # Import the main handler
        print("DEBUG: Importing app.main...", flush=True)
        from app.main import app
        from mangum import Mangum
        print("DEBUG: app.main imported.", flush=True)
        
        # Create Mangum handler
        print("DEBUG: Creating Mangum handler...", flush=True)
        handler = Mangum(app, lifespan="off")
        
        # Call handler
        print("DEBUG: Invoking Mangum handler...", flush=True)
        result = handler(event, context)
        print(f"DEBUG: Mangum returned type: {type(result)}", flush=True)
        
        # Check if result is a coroutine (async function)
        if asyncio.iscoroutine(result):
            print("DEBUG: Result is coroutine, running loop...", flush=True)
            # Run async operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(result)
            finally:
                loop.close()
            print("DEBUG: Loop finished.", flush=True)
        
        status = 'unknown'
        if isinstance(result, dict):
            status = result.get('statusCode')
        
        print(f"DEBUG: Lambda execution completed. Status: {status}", flush=True)
        return result
        
    except BaseException as e:
        print(f"CRITICAL ERROR in lambda_handler: {e}", flush=True)
        traceback.print_exc()
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e),
                "type": type(e).__name__
            }),
            "headers": {"Content-Type": "application/json"}
        }