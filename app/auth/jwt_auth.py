"""JWT Authentication Middleware for API Endpoints

Simple JWT-based authentication for REST API endpoints.
Integrates with existing OTP-based authentication system.
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import settings
from app.omnichannel.authentication.user_repository import UserRepository

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = settings.AWS_ACCOUNT_ID  # Use account ID as secret (simple for MVP)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security scheme
security = HTTPBearer()


class User:
    """Simple user model for JWT auth"""
    def __init__(self, email: str):
        self.email = email


def create_access_token(email: str) -> str:
    """
    Create JWT access token for user
    
    Args:
        email: User's email
        
    Returns:
        JWT token string
    """
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        User email if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        return email
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    email = decode_access_token(token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user exists in database
    user_repo = UserRepository()
    user_data = user_repo.get_user(email)
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return User(email=email)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    Optional authentication - returns None if no token provided
    
    Args:
        credentials: Optional HTTP Bearer token
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
