"""Telegram Bot Service for AgentFirst2 MVP

This module provides Telegram Bot API integration:
- Send messages to users
- Handle webhook updates
- Manage bot commands
"""

import json
import logging
import httpx
from typing import Optional, Dict, Any
from app.config.secrets_manager import SecretsManager

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram Bot API service"""

    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Telegram service

        Args:
            bot_token: Telegram bot token (if None, fetches from Secrets Manager)
        """
        if bot_token:
            self.bot_token = bot_token
        else:
            from app.config.settings import settings
            self.bot_token = settings.TELEGRAM_BOT_TOKEN
            
            if not self.bot_token:
                 logger.info("Telegram Bot Token not found in settings, attempting to fetch from Secrets Manager...")
                 try:
                     self.bot_token = SecretsManager().get_telegram_token()
                     if self.bot_token:
                         logger.info("Successfully retrieved Telegram Bot Token from Secrets Manager")
                 except Exception as e:
                     logger.warning(f"Failed to fetch token from Secrets Manager: {e}")

            if not self.bot_token:
                 logger.warning("Telegram Bot Token not available. Service may fail to send messages.")

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_to_message_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send message to Telegram chat

        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Parse mode (HTML, Markdown, MarkdownV2)
            reply_to_message_id: Reply to message ID

        Returns:
            API response
        """
        try:
            payload = {
                "chat_id": int(chat_id),
                "text": text,
                "parse_mode": parse_mode,
            }

            if reply_to_message_id:
                payload["reply_to_message_id"] = reply_to_message_id

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json=payload,
                    timeout=10.0,
                )

                result = response.json()

                if response.status_code == 200 and result.get("ok"):
                    logger.info(
                        json.dumps({
                            "event": "telegram_message_sent",
                            "chat_id": chat_id,
                            "message_id": result.get("result", {}).get("message_id"),
                        })
                    )
                    return result
                else:
                    logger.error(
                        json.dumps({
                            "event": "telegram_send_failed",
                            "chat_id": chat_id,
                            "status_code": response.status_code,
                            "error": result.get("description", "Unknown error"),
                        })
                    )
                    return {"ok": False, "error": result.get("description")}

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "telegram_send_exception",
                    "chat_id": chat_id,
                    "error": str(e),
                })
            )
            return {"ok": False, "error": str(e)}

    async def send_typing_indicator(self, chat_id: int) -> Dict[str, Any]:
        """
        Send typing indicator to chat

        Args:
            chat_id: Telegram chat ID

        Returns:
            API response
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendChatAction",
                    json={"chat_id": chat_id, "action": "typing"},
                    timeout=10.0,
                )

                result = response.json()

                if response.status_code == 200 and result.get("ok"):
                    logger.info(
                        json.dumps({
                            "event": "telegram_typing_sent",
                            "chat_id": chat_id,
                        })
                    )
                    return result
                else:
                    logger.error(
                        json.dumps({
                            "event": "telegram_typing_failed",
                            "chat_id": chat_id,
                            "error": result.get("description", "Unknown error"),
                        })
                    )
                    return {"ok": False, "error": result.get("description")}

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "telegram_typing_exception",
                    "chat_id": chat_id,
                    "error": str(e),
                })
            )
            return {"ok": False, "error": str(e)}

    async def get_me(self) -> Dict[str, Any]:
        """
        Get bot information

        Returns:
            Bot information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/getMe",
                    timeout=10.0,
                )

                result = response.json()

                if response.status_code == 200 and result.get("ok"):
                    logger.info(
                        json.dumps({
                            "event": "telegram_getme_success",
                            "bot_id": result.get("result", {}).get("id"),
                            "bot_username": result.get("result", {}).get("username"),
                        })
                    )
                    return result
                else:
                    logger.error(
                        json.dumps({
                            "event": "telegram_getme_failed",
                            "error": result.get("description", "Unknown error"),
                        })
                    )
                    return {"ok": False, "error": result.get("description")}

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "telegram_getme_exception",
                    "error": str(e),
                })
            )
            return {"ok": False, "error": str(e)}

    async def set_webhook(
        self,
        url: str,
        allowed_updates: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Set webhook URL for bot

        Args:
            url: Webhook URL
            allowed_updates: List of allowed update types

        Returns:
            API response
        """
        try:
            payload = {"url": url}

            if allowed_updates:
                payload["allowed_updates"] = allowed_updates

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/setWebhook",
                    json=payload,
                    timeout=10.0,
                )

                result = response.json()

                if response.status_code == 200 and result.get("ok"):
                    logger.info(
                        json.dumps({
                            "event": "telegram_webhook_set",
                            "url": url,
                        })
                    )
                    return result
                else:
                    logger.error(
                        json.dumps({
                            "event": "telegram_webhook_failed",
                            "url": url,
                            "error": result.get("description", "Unknown error"),
                        })
                    )
                    return {"ok": False, "error": result.get("description")}

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "telegram_webhook_exception",
                    "url": url,
                    "error": str(e),
                })
            )
            return {"ok": False, "error": str(e)}

    async def delete_webhook(self) -> Dict[str, Any]:
        """
        Delete webhook

        Returns:
            API response
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/deleteWebhook",
                    timeout=10.0,
                )

                result = response.json()

                if response.status_code == 200 and result.get("ok"):
                    logger.info(
                        json.dumps({
                            "event": "telegram_webhook_deleted",
                        })
                    )
                    return result
                else:
                    logger.error(
                        json.dumps({
                            "event": "telegram_webhook_delete_failed",
                            "error": result.get("description", "Unknown error"),
                        })
                    )
                    return {"ok": False, "error": result.get("description")}

        except Exception as e:
            logger.error(
                json.dumps({
                    "event": "telegram_webhook_delete_exception",
                    "error": str(e),
                })
            )
            return {"ok": False, "error": str(e)}
