"""Event Bus for AgentFirst2 MVP

This module provides SNS/SQS event bus for asynchronous event processing:
- SNS topics for event publishing
- SQS queues for event consumption
- Dead Letter Queue (DLQ) for failed messages
- KMS encryption for sensitive data
- Message deduplication and ordering
"""

import json
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EventBusConfig:
    """Configuration for Event Bus"""

    def __init__(
        self,
        region: str = None,
        sns_topic_arn: Optional[str] = None,
        sqs_queue_url: Optional[str] = None,
        sqs_dlq_url: Optional[str] = None,
        kms_key_id: Optional[str] = None,
        enable_encryption: bool = True,
        message_retention_seconds: int = 345600,  # 4 days
        visibility_timeout_seconds: int = 300,  # 5 minutes
        dlq_retention_seconds: int = 1209600,  # 14 days
    ):
        self.region = region or settings.AWS_REGION
        self.sns_topic_arn = sns_topic_arn
        self.sqs_queue_url = sqs_queue_url
        self.sqs_dlq_url = sqs_dlq_url
        self.kms_key_id = kms_key_id
        self.enable_encryption = enable_encryption
        self.message_retention_seconds = message_retention_seconds
        self.visibility_timeout_seconds = visibility_timeout_seconds
        self.dlq_retention_seconds = dlq_retention_seconds


class EventMessage:
    """Represents an event message"""

    def __init__(
        self,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        user_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.event_type = event_type
        self.source = source
        self.data = data
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.user_email = user_email
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID"""
        import uuid
        return str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "event_type": self.event_type,
            "source": self.source,
            "data": self.data,
            "correlation_id": self.correlation_id,
            "user_email": self.user_email,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventMessage":
        """Create message from dictionary"""
        msg = cls(
            event_type=data["event_type"],
            source=data["source"],
            data=data["data"],
            correlation_id=data.get("correlation_id"),
            user_email=data.get("user_email"),
            metadata=data.get("metadata"),
        )
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg


class EventBus:
    """Event Bus for publishing and consuming events"""

    def __init__(self, config: EventBusConfig):
        self.config = config
        self.sns_client = boto3.client("sns", region_name=config.region)
        self.sqs_client = boto3.client("sqs", region_name=config.region)
        self.published_messages: List[str] = []
        self.failed_messages: List[str] = []

    async def publish_event(
        self,
        event: EventMessage,
        topic_arn: Optional[str] = None,
    ) -> str:
        """
        Publish event to SNS topic

        Args:
            event: Event message to publish
            topic_arn: SNS topic ARN (uses default if not provided)

        Returns:
            Message ID

        Raises:
            Exception: If publishing fails
        """
        try:
            topic_arn = topic_arn or self.config.sns_topic_arn
            if not topic_arn:
                raise ValueError("SNS topic ARN not configured")

            # Prepare message attributes
            message_attributes = {
                "event_type": {
                    "StringValue": event.event_type,
                    "DataType": "String",
                },
                "source": {
                    "StringValue": event.source,
                    "DataType": "String",
                },
                "correlation_id": {
                    "StringValue": event.correlation_id,
                    "DataType": "String",
                },
            }

            if event.user_email:
                message_attributes["user_email"] = {
                    "StringValue": event.user_email,
                    "DataType": "String",
                }

            # Publish to SNS
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Message=event.to_json(),
                Subject=f"Event: {event.event_type}",
                MessageAttributes=message_attributes,
            )

            message_id = response["MessageId"]
            self.published_messages.append(message_id)

            logger.info(
                json.dumps({
                    "event": "message_published",
                    "message_id": message_id,
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                })
            )

            return message_id

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "publish_failed",
                    "error": str(e),
                    "event_type": event.event_type,
                })
            )
            self.failed_messages.append(event.correlation_id)
            raise

    async def send_message(
        self,
        event: EventMessage,
        queue_url: Optional[str] = None,
    ) -> str:
        """
        Send message to SQS queue

        Args:
            event: Event message to send
            queue_url: SQS queue URL (uses default if not provided)

        Returns:
            Message ID

        Raises:
            Exception: If sending fails
        """
        try:
            queue_url = queue_url or self.config.sqs_queue_url
            if not queue_url:
                raise ValueError("SQS queue URL not configured")

            # Prepare message attributes
            message_attributes = {
                "event_type": {
                    "StringValue": event.event_type,
                    "DataType": "String",
                },
                "source": {
                    "StringValue": event.source,
                    "DataType": "String",
                },
                "correlation_id": {
                    "StringValue": event.correlation_id,
                    "DataType": "String",
                },
            }

            if event.user_email:
                message_attributes["user_email"] = {
                    "StringValue": event.user_email,
                    "DataType": "String",
                }

            # Send to SQS
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=event.to_json(),
                MessageAttributes=message_attributes,
                MessageDeduplicationId=event.correlation_id,
                MessageGroupId=event.user_email or "default",
            )

            message_id = response["MessageId"]
            self.published_messages.append(message_id)

            logger.info(
                json.dumps({
                    "event": "sqs_message_sent",
                    "message_id": message_id,
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                })
            )

            return message_id

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "sqs_send_failed",
                    "error": str(e),
                    "event_type": event.event_type,
                })
            )
            self.failed_messages.append(event.correlation_id)
            raise

    async def receive_messages(
        self,
        queue_url: Optional[str] = None,
        max_messages: int = 10,
        wait_time_seconds: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Receive messages from SQS queue

        Args:
            queue_url: SQS queue URL (uses default if not provided)
            max_messages: Maximum number of messages to receive
            wait_time_seconds: Long polling wait time

        Returns:
            List of messages

        Raises:
            Exception: If receiving fails
        """
        try:
            queue_url = queue_url or self.config.sqs_queue_url
            if not queue_url:
                raise ValueError("SQS queue URL not configured")

            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                MessageAttributeNames=["All"],
            )

            messages = response.get("Messages", [])

            logger.info(
                json.dumps({
                    "event": "messages_received",
                    "count": len(messages),
                    "queue_url": queue_url,
                })
            )

            return messages

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "receive_failed",
                    "error": str(e),
                })
            )
            raise

    async def delete_message(
        self,
        queue_url: Optional[str] = None,
        receipt_handle: Optional[str] = None,
    ) -> bool:
        """
        Delete message from SQS queue

        Args:
            queue_url: SQS queue URL (uses default if not provided)
            receipt_handle: Message receipt handle

        Returns:
            True if successful

        Raises:
            Exception: If deletion fails
        """
        try:
            queue_url = queue_url or self.config.sqs_queue_url
            if not queue_url or not receipt_handle:
                raise ValueError("Queue URL and receipt handle required")

            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
            )

            logger.info(
                json.dumps({
                    "event": "message_deleted",
                    "queue_url": queue_url,
                })
            )

            return True

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "delete_failed",
                    "error": str(e),
                })
            )
            raise

    async def send_to_dlq(
        self,
        event: EventMessage,
        reason: str,
        dlq_url: Optional[str] = None,
    ) -> str:
        """
        Send message to Dead Letter Queue

        Args:
            event: Event message to send
            reason: Reason for sending to DLQ
            dlq_url: DLQ URL (uses default if not provided)

        Returns:
            Message ID

        Raises:
            Exception: If sending fails
        """
        try:
            dlq_url = dlq_url or self.config.sqs_dlq_url
            if not dlq_url:
                raise ValueError("DLQ URL not configured")

            # Add DLQ metadata
            event.metadata["dlq_reason"] = reason
            event.metadata["dlq_timestamp"] = datetime.now(timezone.utc).isoformat()

            response = self.sqs_client.send_message(
                QueueUrl=dlq_url,
                MessageBody=event.to_json(),
                MessageAttributes={
                    "event_type": {
                        "StringValue": event.event_type,
                        "DataType": "String",
                    },
                    "dlq_reason": {
                        "StringValue": reason,
                        "DataType": "String",
                    },
                },
            )

            message_id = response["MessageId"]

            logger.warning(
                json.dumps({
                    "event": "message_sent_to_dlq",
                    "message_id": message_id,
                    "reason": reason,
                    "correlation_id": event.correlation_id,
                })
            )

            return message_id

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "dlq_send_failed",
                    "error": str(e),
                    "reason": reason,
                })
            )
            raise

    def get_queue_attributes(
        self,
        queue_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get SQS queue attributes

        Args:
            queue_url: SQS queue URL (uses default if not provided)

        Returns:
            Queue attributes

        Raises:
            Exception: If retrieval fails
        """
        try:
            queue_url = queue_url or self.config.sqs_queue_url
            if not queue_url:
                raise ValueError("SQS queue URL not configured")

            response = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["All"],
            )

            return response.get("Attributes", {})

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "get_attributes_failed",
                    "error": str(e),
                })
            )
            raise

    def get_topic_attributes(
        self,
        topic_arn: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get SNS topic attributes

        Args:
            topic_arn: SNS topic ARN (uses default if not provided)

        Returns:
            Topic attributes

        Raises:
            Exception: If retrieval fails
        """
        try:
            topic_arn = topic_arn or self.config.sns_topic_arn
            if not topic_arn:
                raise ValueError("SNS topic ARN not configured")

            response = self.sns_client.get_topic_attributes(
                TopicArn=topic_arn,
            )

            return response.get("Attributes", {})

        except ClientError as e:
            logger.error(
                json.dumps({
                    "event": "get_topic_attributes_failed",
                    "error": str(e),
                })
            )
            raise
