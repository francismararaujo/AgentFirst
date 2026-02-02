"""Merchant API Endpoints

REST API for managing iFood merchants (multi-tenant).
All endpoints require JWT authentication and enforce user isolation.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.jwt_auth import get_current_user, User
from app.repositories.merchant_repository import MerchantRepository
from app.domains.retail.ifood_connector import iFoodConnector
from app.config.secrets_manager import SecretsManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/merchants", tags=["merchants"])


# Pydantic Models
class MerchantCreate(BaseModel):
    """Request model for creating a merchant"""
    merchant_id: str = Field(..., description="iFood merchant ID (store ID)")
    platform: str = Field(default="ifood", description="Platform name")


class MerchantUpdate(BaseModel):
    """Request model for updating a merchant"""
    status: str | None = Field(None, description="Merchant status: active, inactive, suspended")
    polling_enabled: bool | None = Field(None, description="Enable/disable polling")


class MerchantResponse(BaseModel):
    """Response model for merchant data"""
    merchant_id: str
    user_email: str
    platform: str
    status: str
    polling_enabled: bool
    created_at: int
    updated_at: int
    last_poll_success: int | None
    last_poll_error: str | None


class MerchantListResponse(BaseModel):
    """Response model for list of merchants"""
    merchants: List[MerchantResponse]
    count: int


class ValidationRequest(BaseModel):
    """Request model for validating merchant ID"""
    merchant_id: str = Field(..., description="iFood merchant ID to validate")


class ValidationResponse(BaseModel):
    """Response model for validation result"""
    valid: bool
    message: str


# Endpoints
@router.post("", response_model=MerchantResponse, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    data: MerchantCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new merchant (onboarding)
    
    Validates merchant_id with iFood API before creating.
    Requires JWT authentication.
    """
    merchant_repo = MerchantRepository()
    
    # Check if merchant already exists for this user
    existing = merchant_repo.get_merchant(data.merchant_id, current_user.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Merchant already exists for this user"
        )
    
    # Validate merchant_id with iFood API
    try:
        secrets_manager = SecretsManager()
        connector = iFoodConnector(secrets_manager, data.merchant_id)
        
        # Try to authenticate (validates credentials + merchant_id)
        if not await connector.authenticate():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid merchant ID or authentication failed"
            )
        
        logger.info(f"Merchant {data.merchant_id} validated successfully")
        
    except Exception as e:
        logger.error(f"Validation failed for merchant {data.merchant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Merchant validation failed: {str(e)}"
        )
    
    # Create merchant in DynamoDB
    success = merchant_repo.create_merchant({
        'merchant_id': data.merchant_id,
        'user_email': current_user.email,
        'platform': data.platform,
        'status': 'active',
        'polling_enabled': True
    })
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create merchant"
        )
    
    # Retrieve and return created merchant
    merchant = merchant_repo.get_merchant(data.merchant_id, current_user.email)
    return MerchantResponse(**merchant)


@router.get("", response_model=MerchantListResponse)
async def list_merchants(current_user: User = Depends(get_current_user)):
    """
    List all merchants for the authenticated user
    
    Returns only merchants owned by the current user.
    """
    merchant_repo = MerchantRepository()
    merchants = merchant_repo.get_merchants_by_user(current_user.email)
    
    return MerchantListResponse(
        merchants=[MerchantResponse(**m) for m in merchants],
        count=len(merchants)
    )


@router.get("/{merchant_id}", response_model=MerchantResponse)
async def get_merchant(
    merchant_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific merchant
    
    Returns 404 if merchant doesn't exist or doesn't belong to user.
    """
    merchant_repo = MerchantRepository()
    merchant = merchant_repo.get_merchant(merchant_id, current_user.email)
    
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )
    
    return MerchantResponse(**merchant)


@router.put("/{merchant_id}", response_model=MerchantResponse)
async def update_merchant(
    merchant_id: str,
    updates: MerchantUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update merchant settings
    
    Can update status and polling_enabled.
    Returns 404 if merchant doesn't exist or doesn't belong to user.
    """
    merchant_repo = MerchantRepository()
    
    # Verify merchant exists and belongs to user
    existing = merchant_repo.get_merchant(merchant_id, current_user.email)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )
    
    # Build updates dict (only include non-None values)
    update_data = updates.dict(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided"
        )
    
    # Update merchant
    success = merchant_repo.update_merchant(
        merchant_id,
        current_user.email,
        update_data
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update merchant"
        )
    
    # Return updated merchant
    merchant = merchant_repo.get_merchant(merchant_id, current_user.email)
    return MerchantResponse(**merchant)


@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant(
    merchant_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete (deactivate) a merchant
    
    Soft delete: sets status to 'inactive' and polling_enabled to False.
    Returns 404 if merchant doesn't exist or doesn't belong to user.
    """
    merchant_repo = MerchantRepository()
    
    # Verify merchant exists and belongs to user
    existing = merchant_repo.get_merchant(merchant_id, current_user.email)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )
    
    # Soft delete
    success = merchant_repo.delete_merchant(merchant_id, current_user.email)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete merchant"
        )
    
    return None


@router.post("/validate", response_model=ValidationResponse)
async def validate_merchant_id(
    data: ValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate a merchant ID with iFood API
    
    Useful for onboarding flow to check if merchant ID is valid
    before creating the merchant.
    """
    try:
        secrets_manager = SecretsManager()
        connector = iFoodConnector(secrets_manager, data.merchant_id)
        
        # Try to authenticate
        if await connector.authenticate():
            return ValidationResponse(
                valid=True,
                message="Merchant ID is valid"
            )
        else:
            return ValidationResponse(
                valid=False,
                message="Authentication failed - invalid merchant ID"
            )
            
    except Exception as e:
        logger.error(f"Validation error for merchant {data.merchant_id}: {e}")
        return ValidationResponse(
            valid=False,
            message=f"Validation failed: {str(e)}"
        )


@router.get("/{merchant_id}/status")
async def get_merchant_status(
    merchant_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get polling status for a merchant
    
    Returns detailed polling information including last success/error.
    """
    merchant_repo = MerchantRepository()
    merchant = merchant_repo.get_merchant(merchant_id, current_user.email)
    
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found"
        )
    
    return {
        "merchant_id": merchant['merchant_id'],
        "polling_enabled": merchant['polling_enabled'],
        "status": merchant['status'],
        "last_poll_success": merchant.get('last_poll_success'),
        "last_poll_error": merchant.get('last_poll_error'),
        "is_healthy": merchant.get('last_poll_success') is not None and merchant.get('last_poll_error') is None
    }
