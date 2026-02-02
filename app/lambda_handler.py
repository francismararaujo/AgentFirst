"""AWS Lambda handler for AgentFirst2 MVP

This module provides the AWS Lambda entry point with:
- X-Ray tracing for distributed tracing
- CloudWatch structured logging (JSON format)
- Request/response validation
- Error handling and recovery
- Performance monitoring
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

# Add lambda-deps to Python path for Lambda environment
# In Lambda, the working directory is /var/task
lambda_deps_path = '/var/task/lambda-deps'
if os.path.exists(lambda_deps_path) and lambda_deps_path not in sys.path:
    sys.path.insert(0, lambda_deps_path)

# Fallback for local development
local_lambda_deps = os.path.join(os.path.dirname(__file__), '..', 'lambda-deps')
if os.path.exists(local_lambda_deps) and local_lambda_deps not in sys.path:
    sys.path.insert(0, local_lambda_deps)

from mangum import Mangum
handler = Mangum(app, lifespan="off")
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
from aws_xray_sdk.core.context import Context as XRayContext

from app.main import app
from app.config.settings import settings

# Configure structured logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Patch AWS SDK for X-Ray tracing
if settings.XRAY_ENABLED:
    patch_all()


# Create Mangum handler for FastAPI
handler = Mangum(app, lifespan="off")


class LambdaMetrics:
    """Track Lambda execution metrics"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration_ms = 0
        self.memory_used = 0
        self.error_count = 0

    def start(self):
        """Start timing"""
        self.start_time = time.time()

    def end(self):
        """End timing and calculate duration"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "duration_ms": round(self.duration_ms, 2),
            "memory_used": self.memory_used,
            "error_count": self.error_count
        }


def _log_structured(
    level: str,
    message: str,
    **kwargs
) -> None:
    """
    Log structured message in JSON format

    Args:
        level: Log level (INFO, ERROR, WARNING, DEBUG)
        message: Log message
        **kwargs: Additional fields to include in JSON
    """
    log_data = {
        "timestamp": time.time(),
        "level": level,
        "message": message,
        **kwargs
    }

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(json.dumps(log_data))


def _extract_request_info(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract request information from Lambda event

    Args:
        event: Lambda event

    Returns:
        Dictionary with request info
    """
    return {
        "method": event.get("httpMethod", "UNKNOWN"),
        "path": event.get("path", "UNKNOWN"),
        "source_ip": event.get("requestContext", {}).get("identity", {}).get("sourceIp", "UNKNOWN"),
        "user_agent": event.get("headers", {}).get("User-Agent", "UNKNOWN"),
        "request_id": event.get("requestContext", {}).get("requestId", "UNKNOWN"),
    }


def _validate_event(event: Dict[str, Any]) -> bool:
    """
    Validate Lambda event structure

    Args:
        event: Lambda event

    Returns:
        True if event is valid
    """
    required_fields = ["httpMethod", "path"]
    return all(field in event for field in required_fields)


@xray_recorder.capture("lambda_handler")
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for AgentFirst2 MVP

    Handles:
    - Request validation
    - X-Ray tracing
    - Structured logging
    - Error handling
    - Performance monitoring

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        Lambda response with status code and body
    """
    metrics = LambdaMetrics()
    metrics.start()

    try:
        # Extract request info
        request_info = _extract_request_info(event)

        # Log incoming request
        _log_structured(
            "INFO",
            "Received Lambda event",
            **request_info,
            event_type=event.get("requestContext", {}).get("eventSource", "UNKNOWN")
        )

        # Validate event structure
        if not _validate_event(event):
            _log_structured(
                "ERROR",
                "Invalid Lambda event structure",
                **request_info
            )
            metrics.error_count += 1
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid request",
                    "message": "Missing required fields"
                }),
                "headers": {"Content-Type": "application/json"}
            }

        # Call Mangum handler
        response = handler(event, context)

        # Log response
        _log_structured(
            "INFO",
            "Lambda request completed successfully",
            **request_info,
            status_code=response.get("statusCode", 200)
        )

        return response

    except Exception as e:
        metrics.error_count += 1

        # Log error with full context
        _log_structured(
            "ERROR",
            f"Error in lambda_handler: {str(e)}",
            **request_info,
            error_type=type(e).__name__,
            error_message=str(e),
            traceback=True
        )

        # Return error response
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e) if settings.DEBUG else "An error occurred",
                "request_id": request_info.get("request_id")
            }),
            "headers": {"Content-Type": "application/json"}
        }

    finally:
        metrics.end()

        # Log metrics
        _log_structured(
            "INFO",
            "Lambda execution metrics",
            **metrics.to_dict(),
            memory_limit_in_mb=context.memory_limit_in_mb if context else "UNKNOWN"
        )
