import jwt
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from .config import settings

logger = logging.getLogger(__name__)


class JWTValidationError(Exception):
    pass


def validate_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Validate a Supabase JWT token and return the decoded payload
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload containing user info
        
    Raises:
        JWTValidationError: If token is invalid or expired
    """
    try:
        # Decode and verify JWT
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        # Check expiration
        if "exp" in payload:
            exp_timestamp = payload["exp"]
            if datetime.utcnow().timestamp() > exp_timestamp:
                raise JWTValidationError("Token has expired")
        
        # Validate required fields
        if "sub" not in payload:
            raise JWTValidationError("Token missing user ID (sub)")
        
        if "email" not in payload:
            logger.warning("Token missing email field")
        
        logger.info(f"Successfully validated token for user: {payload.get('sub')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise JWTValidationError("Token has expired")
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise JWTValidationError(f"Invalid token: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error validating JWT: {e}")
        raise JWTValidationError(f"Token validation failed: {str(e)}")


def get_user_id_from_token(token: str) -> str:
    """
    Extract user ID from a validated token
    
    Args:
        token: JWT token string
        
    Returns:
        User ID string
        
    Raises:
        JWTValidationError: If token is invalid
    """
    try:
        payload = validate_supabase_jwt(token)
        return payload["sub"]
    except JWTValidationError:
        raise
    except Exception as e:
        raise JWTValidationError(f"Failed to extract user ID: {str(e)}")


def create_auth_exception(message: str = "Could not validate credentials") -> HTTPException:
    """Create a standardized authentication exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )