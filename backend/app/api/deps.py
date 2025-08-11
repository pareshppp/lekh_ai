from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..core.security import validate_supabase_jwt, create_auth_exception, JWTValidationError
import logging

logger = logging.getLogger(__name__)

# Security scheme for extracting Bearer tokens
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate user from JWT token
    
    Returns:
        Dictionary containing user information from the JWT payload
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    try:
        if not credentials:
            logger.warning("No credentials provided")
            raise create_auth_exception("No authentication credentials provided")
        
        token = credentials.credentials
        if not token:
            logger.warning("Empty token provided")
            raise create_auth_exception("Empty authentication token")
        
        # Validate the token and get user info
        user_payload = validate_supabase_jwt(token)
        
        logger.info(f"Authenticated user: {user_payload.get('email', 'unknown')}")
        return user_payload
        
    except JWTValidationError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise create_auth_exception(str(e))
        
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise create_auth_exception("Authentication failed")


def get_current_user_id(current_user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """
    FastAPI dependency to extract user ID from authenticated user
    
    Returns:
        User ID string
        
    Raises:
        HTTPException: If user ID is not available
    """
    user_id = current_user.get("sub")
    if not user_id:
        logger.error("User ID not found in token payload")
        raise create_auth_exception("User ID not found in token")
    
    return user_id