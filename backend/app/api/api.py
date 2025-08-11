from fastapi import APIRouter
from .endpoints import stories

api_router = APIRouter()

# Include story endpoints
api_router.include_router(stories.router, tags=["stories"])

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "lekh-api"}