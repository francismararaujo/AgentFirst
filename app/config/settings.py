"""Configuration settings for AgentFirst2 MVP"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"

    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCOUNT_ID: str = os.getenv("AWS_ACCOUNT_ID", "")

    # DynamoDB Configuration
    DYNAMODB_ENDPOINT: Optional[str] = os.getenv("DYNAMODB_ENDPOINT", None)
    DYNAMODB_USERS_TABLE: str = os.getenv("DYNAMODB_USERS_TABLE", "agentfirst-users")
    DYNAMODB_SESSIONS_TABLE: str = os.getenv("DYNAMODB_SESSIONS_TABLE", "agentfirst-sessions")
    DYNAMODB_MEMORY_TABLE: str = os.getenv("DYNAMODB_MEMORY_TABLE", "agentfirst-memory")
    DYNAMODB_USAGE_TABLE: str = os.getenv("DYNAMODB_USAGE_TABLE", "agentfirst-usage")
    DYNAMODB_AUDIT_TABLE: str = os.getenv("DYNAMODB_AUDIT_TABLE", "agentfirst-audit-logs")
    DYNAMODB_ESCALATION_TABLE: str = os.getenv("DYNAMODB_ESCALATION_TABLE", "agentfirst-escalation")
    DYNAMODB_OTP_TABLE: str = os.getenv("DYNAMODB_OTP_TABLE", "agentfirst-otp")

    # SNS Configuration
    SNS_OMNICHANNEL_TOPIC_ARN: str = os.getenv("SNS_OMNICHANNEL_TOPIC_ARN", "")
    SNS_RETAIL_TOPIC_ARN: str = os.getenv("SNS_RETAIL_TOPIC_ARN", "")

    # SQS Configuration
    SQS_QUEUE_URL: str = os.getenv("SQS_QUEUE_URL", "")
    SQS_DLQ_URL: str = os.getenv("SQS_DLQ_URL", "")

    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    BEDROCK_REGION: str = os.getenv("BEDROCK_REGION", "us-east-1")

    # Email Configuration (SES)
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "naoresponder@agentfirst.com.br")

    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", None)
    TELEGRAM_WEBHOOK_URL: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL", None)

    # iFood Configuration
    IFOOD_CLIENT_ID: Optional[str] = os.getenv("IFOOD_CLIENT_ID", None)
    IFOOD_CLIENT_SECRET: Optional[str] = os.getenv("IFOOD_CLIENT_SECRET", None)
    IFOOD_API_URL: str = os.getenv("IFOOD_API_URL", "https://api.ifood.com.br")
    IFOOD_POLLING_INTERVAL: int = int(os.getenv("IFOOD_POLLING_INTERVAL", "30"))

    # Secrets Manager Configuration
    SECRETS_MANAGER_REGION: str = os.getenv("SECRETS_MANAGER_REGION", "us-east-1")

    # Billing Configuration
    FREE_TIER_LIMIT: int = int(os.getenv("FREE_TIER_LIMIT", "100"))
    PRO_TIER_LIMIT: int = int(os.getenv("PRO_TIER_LIMIT", "10000"))
    ENTERPRISE_TIER_LIMIT: int = int(os.getenv("ENTERPRISE_TIER_LIMIT", "999999999"))

    # Session Configuration
    SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", "24"))

    # Audit Configuration
    AUDIT_LOG_TTL_DAYS: int = int(os.getenv("AUDIT_LOG_TTL_DAYS", "365"))

    # API Configuration
    API_TITLE: str = "AgentFirst2 MVP"
    API_VERSION: str = "0.1.0"
    API_DESCRIPTION: str = "Omnichannel AI platform for retail operations"

    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "json"

    # X-Ray Configuration
    XRAY_ENABLED: bool = ENVIRONMENT != "test"


# Global settings instance
settings = Settings()
