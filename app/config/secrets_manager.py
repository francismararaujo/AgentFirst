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
        Retrieve a secret from AWS Secrets Manager or Environment Variables (Local Dev)

        Args:
            secret_name: Name of the secret
            use_cache: Whether to use cached value

        Returns:
            Secret value as dictionary, or None if not found
        """
        # 1. Check Cache
        if use_cache and secret_name in self._cache:
            logger.debug(f"Using cached secret: {secret_name}")
            return self._cache[secret_name]

        # 2. Check Environment Variables (Local Fallback / Override)
        # Convert secret name "AgentFirst/ifood-credentials" -> "IFOD_CREDENTIALS" or similar logic?
        # Better: Check for specific ENV VARS that map to this secret's known keys
        
        # Mappings for specific known secrets to Env Vars structure
        env_secret = self._get_from_env(secret_name)
        if env_secret:
            logger.info(f"Using environment variable for secret: {secret_name}")
            self._cache[secret_name] = env_secret
            return env_secret

        # 3. Retrieve from AWS Secrets Manager
        try:
            response = self.client.get_secret_value(SecretId=secret_name)

            # Parse secret value
            if "SecretString" in response:
                secret_value = json.loads(response["SecretString"])
            else:
                secret_value = response["SecretBinary"]

            # Cache the secret
            self._cache[secret_name] = secret_value
            logger.info(f"Retrieved secret from AWS: {secret_name}")

            return secret_value

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                logger.warning(f"Secret not found in AWS: {secret_name}")
            elif error_code in ["UnrecognizedClientException", "InvalidClientTokenId", "AuthFailure"]:
                 logger.warning(f"AWS Auth failed for {secret_name}, and no local env var found. ({error_code})")
            else:
                logger.error(f"Error retrieving secret {secret_name}: {error_code}")
            return None

    def _get_from_env(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Helper to map secret names to environment variables"""
        import os
        
        if "ifood" in secret_name.lower():
            # Check for standard iFood env vars
            client_id = os.getenv("IFOOD_CLIENT_ID")
            client_secret = os.getenv("IFOOD_CLIENT_SECRET")
            merchant_id = os.getenv("IFOOD_MERCHANT_ID")
            webhook_secret = os.getenv("IFOOD_WEBHOOK_SECRET")
            
            if client_id and client_secret:
                return {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "merchant_id": merchant_id,
                    "webhook_secret": webhook_secret
                }
                
        elif "telegram" in secret_name.lower():
             token = os.getenv("TELEGRAM_BOT_TOKEN")
             if token:
                 return {
                     "bot_token": token,
                     "chat_id": os.getenv("TELEGRAM_CHAT_ID")
                 }
                 
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
