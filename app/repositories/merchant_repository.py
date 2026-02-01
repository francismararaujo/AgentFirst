"""Merchant Repository for multi-tenant iFood integration

This module provides data access methods for managing merchants in DynamoDB.
Each merchant represents a customer's iFood store with their own credentials.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MerchantRepository:
    """Repository for managing merchants in DynamoDB"""

    def __init__(self):
        """Initialize DynamoDB client"""
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
        self.table = self.dynamodb.Table(settings.DYNAMODB_MERCHANTS_TABLE)

    def get_active_merchants(self) -> List[Dict[str, Any]]:
        """
        Get all active merchants with polling enabled
        
        Returns:
            List of merchant dictionaries with credentials
        """
        try:
            response = self.table.query(
                IndexName='status-index',
                KeyConditionExpression='#status = :status',
                FilterExpression='polling_enabled = :enabled',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'active',
                    ':enabled': True
                }
            )
            
            merchants = response.get('Items', [])
            logger.info(f"Retrieved {len(merchants)} active merchants")
            return merchants
            
        except ClientError as e:
            logger.error(f"Error retrieving active merchants: {e}")
            return []

    def get_merchant(self, merchant_id: str, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific merchant by ID and user email
        
        Args:
            merchant_id: iFood merchant ID
            user_email: Owner's email
            
        Returns:
            Merchant dictionary or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'merchant_id': merchant_id,
                    'user_email': user_email
                }
            )
            return response.get('Item')
            
        except ClientError as e:
            logger.error(f"Error retrieving merchant {merchant_id}: {e}")
            return None

    def get_merchants_by_user(self, user_email: str) -> List[Dict[str, Any]]:
        """
        Get all merchants for a specific user
        
        Args:
            user_email: User's email
            
        Returns:
            List of merchant dictionaries
        """
        try:
            response = self.table.query(
                IndexName='user-email-index',
                KeyConditionExpression='user_email = :email',
                ExpressionAttributeValues={
                    ':email': user_email
                }
            )
            return response.get('Items', [])
            
        except ClientError as e:
            logger.error(f"Error retrieving merchants for user {user_email}: {e}")
            return []

    def create_merchant(self, data: Dict[str, Any]) -> bool:
        """
        Create a new merchant
        
        Args:
            data: Merchant data including:
                - merchant_id: iFood merchant ID
                - user_email: Owner's email
                - ifood_credentials: Dict with client_id, client_secret, webhook_secret
                - status: 'active' | 'inactive' | 'suspended'
                - polling_enabled: bool
                
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            
            item = {
                'merchant_id': data['merchant_id'],
                'user_email': data['user_email'],
                'ifood_credentials': data['ifood_credentials'],
                'status': data.get('status', 'active'),
                'polling_enabled': data.get('polling_enabled', True),
                'created_at': timestamp,
                'updated_at': timestamp,
                'last_poll_success': None,
                'last_poll_error': None
            }
            
            self.table.put_item(Item=item)
            logger.info(f"Created merchant {data['merchant_id']}")
            return True
            
        except ClientError as e:
            logger.error(f"Error creating merchant: {e}")
            return False

    def update_merchant(self, merchant_id: str, user_email: str, updates: Dict[str, Any]) -> bool:
        """
        Update merchant data
        
        Args:
            merchant_id: iFood merchant ID
            user_email: Owner's email
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            
            # Build update expression
            update_expr = "SET updated_at = :timestamp"
            expr_values = {':timestamp': timestamp}
            expr_names = {}
            
            for key, value in updates.items():
                if key not in ['merchant_id', 'user_email', 'created_at']:
                    placeholder = f":{key}"
                    # Handle reserved keywords
                    if key == 'status':
                        expr_names['#status'] = 'status'
                        update_expr += f", #status = {placeholder}"
                    else:
                        update_expr += f", {key} = {placeholder}"
                    expr_values[placeholder] = value
            
            self.table.update_item(
                Key={
                    'merchant_id': merchant_id,
                    'user_email': user_email
                },
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ExpressionAttributeNames=expr_names if expr_names else None
            )
            
            logger.info(f"Updated merchant {merchant_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error updating merchant {merchant_id}: {e}")
            return False

    def update_poll_status(
        self, 
        merchant_id: str, 
        user_email: str,
        success: bool, 
        error: Optional[str] = None
    ) -> bool:
        """
        Update polling status for a merchant
        
        Args:
            merchant_id: iFood merchant ID
            user_email: Owner's email
            success: Whether the poll was successful
            error: Error message if failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(datetime.utcnow().timestamp())
            
            if success:
                self.table.update_item(
                    Key={
                        'merchant_id': merchant_id,
                        'user_email': user_email
                    },
                    UpdateExpression="SET last_poll_success = :timestamp, last_poll_error = :null",
                    ExpressionAttributeValues={
                        ':timestamp': timestamp,
                        ':null': None
                    }
                )
            else:
                self.table.update_item(
                    Key={
                        'merchant_id': merchant_id,
                        'user_email': user_email
                    },
                    UpdateExpression="SET last_poll_error = :error, updated_at = :timestamp",
                    ExpressionAttributeValues={
                        ':error': error,
                        ':timestamp': timestamp
                    }
                )
            
            return True
            
        except ClientError as e:
            logger.error(f"Error updating poll status for {merchant_id}: {e}")
            return False

    def delete_merchant(self, merchant_id: str, user_email: str) -> bool:
        """
        Delete a merchant (soft delete by setting status to inactive)
        
        Args:
            merchant_id: iFood merchant ID
            user_email: Owner's email
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_merchant(
            merchant_id, 
            user_email,
            {'status': 'inactive', 'polling_enabled': False}
        )
