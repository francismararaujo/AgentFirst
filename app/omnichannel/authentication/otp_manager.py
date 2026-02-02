
"""OTP Manager for secure authentication

This module manages One-Time Passwords (OTP):
- Generation (cryptographically secure)
- Storage (DynamoDB with TTL)
- Verification
"""

import boto3
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from app.config.settings import settings
from app.core.email_service import EmailService

logger = logging.getLogger(__name__)


class OTPManager:
    """Manages One-Time Passwords"""

    def __init__(self, email_service: EmailService):
        """
        Initialize OTP Manager
        
        Args:
            email_service: Service to send emails
        """
        self.email_service = email_service
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        self.table = self.dynamodb.Table(settings.DYNAMODB_OTP_TABLE)
        self.otp_ttl_minutes = 5

    def generate_otp(self) -> str:
        """
        Generate a 6-digit cryptographically secure OTP
        
        Returns:
            6-digit string
        """
        return "".join(secrets.choice("0123456789") for _ in range(6))

    async def send_otp(self, email: str) -> bool:
        """
        Generate, save, and send OTP to email
        
        Args:
            email: User email
            
        Returns:
            True if sent successfull, False otherwise
        """
        try:
            # Generate code
            otp_code = self.generate_otp()
            
            # Calculate expiration
            # Use int timestamp for DynamoDB TTL
            expires_at = int((datetime.now(timezone.utc) + timedelta(minutes=self.otp_ttl_minutes)).timestamp())
            
            # Save to DynamoDB
            self.table.put_item(
                Item={
                    "email": email,
                    "otp_code": otp_code,
                    "expires_at": expires_at,
                    "attempts": 0,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Send email
            sent = self.email_service.send_otp_email(email, otp_code)
            
            if sent:
                logger.info(f"OTP sent to {email}")
                return True
            else:
                logger.error(f"Failed to send OTP email to {email}")
                return False
                
        except Exception as e:
            logger.error(f"Error in send_otp: {str(e)}")
            return False

    async def verify_otp(self, email: str, code: str) -> Dict[str, Any]:
        """
        Verify if OTP is valid
        
        Args:
            email: User email
            code: Code provided by user
            
        Returns:
            Dict with keys: success (bool), message (str)
        """
        try:
            # Get latest OTP for email
            response = self.table.get_item(Key={"email": email})
            
            if "Item" not in response:
                return {
                    "success": False,
                    "message": "Nenhum código encontrado para este e-mail. Solicite um novo."
                }
                
            item = response["Item"]
            stored_otp = item.get("otp_code")
            expires_at = item.get("expires_at")
            attempts = int(item.get("attempts", 0))
            
            # Check expiration
            current_time = int(datetime.now(timezone.utc).timestamp())
            if current_time > expires_at:
                return {
                    "success": False,
                    "message": "Este código expirou. Por favor, solicite um novo."
                }
                
            # Check Max Attempts (e.g., 3)
            if attempts >= 3:
                # Delete sensitive OTP
                self.table.delete_item(Key={"email": email})
                return {
                    "success": False,
                    "message": "Muitas tentativas falhas. O código foi invalidado."
                }
                
            # Verify Code
            if code == stored_otp:
                # Success! Consume the OTP so it can't be reused
                self.table.delete_item(Key={"email": email})
                logger.info(f"OTP verified successfully for {email}")
                return {
                    "success": True, 
                    "message": "Código verificado com sucesso!"
                }
            else:
                # Increment attempts
                self.table.update_item(
                    Key={"email": email},
                    UpdateExpression="SET attempts = attempts + :val",
                    ExpressionAttributeValues={":val": 1}
                )
                return {
                    "success": False,
                    "message": "Código incorreto. Tente novamente."
                }
                
        except Exception as e:
            logger.error(f"Error verifying OTP: {str(e)}")
            return {
                "success": False,
                "message": "Erro ao verificar código. Tente novamente."
            }
