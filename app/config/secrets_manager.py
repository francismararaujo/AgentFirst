"""AWS Secrets Manager integration for AgentFirst2 MVP"""

import json
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError

from app.config.settings import settings

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages secrets from AWS Secrets Manager"""

    def __init__(self):
        """Initialize Secrets Manager client"""
        self.client = boto3.client(
            "secretsmanager",
            region_name=settings.SECRETS_MANAGER_REGION
        )
        self._cache: Dict[str, Any] = {}

    def get_secret(self, secret_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve a secret from AWS Secrets Manager

        Args:
            secret_name: Name of the secret
            use_cache: Whether to use cached value

        Returns:
            Secret value as dictionary, or None if not found
        """
        try:
            # Check cache first
            if use_cache and secret_name in self._cache:
                logger.debug(f"Using cached secret: {secret_name}")
                return self._cache[secret_name]

            # Retrieve from Secrets Manager
            response = self.client.get_secret_value(SecretId=secret_name)

            # Parse secret value
            if "SecretString" in response:
                secret_value = json.loads(response["SecretString"])
            else:
                secret_value = response["SecretBinary"]

            # Cache the secret
            self._cache[secret_name] = secret_value
            logger.info(f"Retrieved secret: {secret_name}")

            return secret_value

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                logger.warning(f"Secret not found: {secret_name}")
            elif error_code == "InvalidRequestException":
                logger.error(f"Invalid request for secret: {secret_name}")
            elif error_code == "InvalidParameterException":
                logger.error(f"Invalid parameter for secret: {secret_name}")
            else:
                logger.error(f"Error retrieving secret {secret_name}: {error_code}")
            return None

    def get_telegram_token(self) -> Optional[str]:
        """Get Telegram bot token from Secrets Manager"""
        # Secret Name verified via CLI: AgentFirst/telegram-bot-token
        secret = self.get_secret("AgentFirst/telegram-bot-token")
        if secret and isinstance(secret, dict):
            # Key verified via CLI: bot_token
            return secret.get("bot_token")
        return secret

    def get_telegram_chat_id(self) -> Optional[str]:
        """Get Telegram chat ID from Secrets Manager"""
        secret = self.get_secret("AgentFirst/telegram-bot-token")
        if secret and isinstance(secret, dict):
            return secret.get("chat_id")
        return None

    def get_ifood_credentials(self) -> Optional[Dict[str, str]]:
        """Get iFood OAuth credentials from Secrets Manager"""
        secret = self.get_secret("ifood-oauth-credentials")
        if secret and isinstance(secret, dict):
            return {
                "client_id": secret.get("client_id"),
                "client_secret": secret.get("client_secret")
            }
        return None

    def get_bedrock_key(self) -> Optional[str]:
        """Get Bedrock API key from Secrets Manager"""
        secret = self.get_secret("bedrock-api-key")
        if secret and isinstance(secret, dict):
            return secret.get("api_key")
        return secret

    def get_database_credentials(self) -> Optional[Dict[str, str]]:
        """Get database credentials from Secrets Manager"""
        secret = self.get_secret("database-credentials")
        if secret and isinstance(secret, dict):
            return {
                "username": secret.get("username"),
                "password": secret.get("password"),
                "host": secret.get("host"),
                "port": secret.get("port"),
                "database": secret.get("database")
            }
        return None

    def clear_cache(self, secret_name: Optional[str] = None):
        """
        Clear cached secrets

        Args:
            secret_name: Specific secret to clear, or None to clear all
        """
        if secret_name:
            if secret_name in self._cache:
                del self._cache[secret_name]
                logger.info(f"Cleared cache for secret: {secret_name}")
        else:
            self._cache.clear()
            logger.info("Cleared all cached secrets")


# Global secrets manager instance
secrets_manager = SecretsManager()
