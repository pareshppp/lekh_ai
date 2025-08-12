import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api import api_router
from app.api.deps import get_current_user_id
from app.websocket.manager import manager
from app.db.supabase_handler import SupabaseHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Initialize Supabase handler for WebSocket auth
supabase_handler = SupabaseHandler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Lekh API server")
    try:
        await manager.initialize_redis()
        logger.info("WebSocket manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Lekh API server")
    try:
        await manager.cleanup()
        logger.info("WebSocket manager cleanup completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Lekh AI Story Generation API",
    description="API for collaborative AI story generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lekh AI Story Generation API",
        "version": "1.0.0",
        "status": "running"
    }


async def verify_websocket_auth(token: str) -> str:
    """
    Verify WebSocket authentication token and return user_id
    
    Args:
        token: JWT token from query parameter
        
    Returns:
        user_id if authentication successful
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        from app.core.security import get_user_id_from_token, JWTValidationError
        
        user_id = get_user_id_from_token(token)
        return user_id
        
    except JWTValidationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


async def verify_story_access(story_id: str, user_id: str) -> bool:
    """
    Verify that the user has access to the story
    
    Args:
        story_id: The story ID
        user_id: The user ID
        
    Returns:
        True if user has access, False otherwise
    """
    try:
        story = await supabase_handler.get_story_by_id(story_id, user_id)
        return story is not None
    except Exception as e:
        logger.error(f"Error verifying story access: {e}")
        return False


@app.websocket("/ws/stories/{story_id}")
async def websocket_endpoint(websocket: WebSocket, story_id: str):
    """
    WebSocket endpoint for real-time story updates
    
    Args:
        websocket: WebSocket connection
        story_id: The story ID to subscribe to
    """
    try:
        # Accept the connection first to enable parameter exchange
        await websocket.accept()
        
        # Wait for authentication message
        try:
            auth_message = await websocket.receive_text()
            import json
            auth_data = json.loads(auth_message)
            
            if auth_data.get("type") != "auth":
                raise ValueError("First message must be authentication")
                
            token = auth_data.get("token")
            if not token:
                raise ValueError("Token is required")
                
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "auth_error",
                "message": "Authentication required"
            }))
            await websocket.close()
            return
        
        # Verify authentication
        try:
            user_id = await verify_websocket_auth(token)
        except HTTPException as e:
            await websocket.send_text(json.dumps({
                "type": "auth_error", 
                "message": e.detail
            }))
            await websocket.close()
            return
        
        # Verify story access
        has_access = await verify_story_access(story_id, user_id)
        if not has_access:
            await websocket.send_text(json.dumps({
                "type": "access_error",
                "message": "Access denied to this story"
            }))
            await websocket.close()
            return
        
        logger.info(f"WebSocket authenticated for user {user_id} on story {story_id}")
        
        # Send authentication success
        await websocket.send_text(json.dumps({
            "type": "auth_success",
            "message": "Authentication successful"
        }))
        
        # Handle the WebSocket communication
        await manager.handle_websocket_communication(websocket, story_id)
        
    except Exception as e:
        logger.error(f"WebSocket error for story {story_id}: {e}")
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.debug else False
    )