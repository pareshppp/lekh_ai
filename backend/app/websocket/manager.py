import json
import asyncio
import logging
import redis.asyncio as redis
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and Redis pub/sub for real-time story updates
    """
    
    def __init__(self):
        # Store active connections by story_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Redis client for pub/sub
        self.redis_client = None
        # Pub/sub instance
        self.pubsub = None
        # Background task for listening to Redis
        self.redis_listener_task = None
        
    async def initialize_redis(self):
        """Initialize Redis connection and pub/sub"""
        try:
            self.redis_client = redis.from_url(
                settings.celery_broker_url,
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            
            # Start Redis listener task
            self.redis_listener_task = asyncio.create_task(self._redis_listener())
            
            logger.info("WebSocket manager Redis connection initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis for WebSocket manager: {e}")
            raise
    
    async def connect(self, websocket: WebSocket, story_id: str):
        """
        Accept a WebSocket connection and subscribe to the story's updates
        
        Args:
            websocket: The WebSocket connection
            story_id: The story ID to subscribe to
        """
        try:
            await websocket.accept()
            
            # Add connection to active connections
            if story_id not in self.active_connections:
                self.active_connections[story_id] = set()
                # Subscribe to the story's Redis channel
                await self.pubsub.subscribe(f"story:{story_id}")
                
            self.active_connections[story_id].add(websocket)
            
            logger.info(f"WebSocket connected for story {story_id}. Active connections: {len(self.active_connections[story_id])}")
            
            # Send connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "story_id": story_id,
                "message": "Connected to story updates"
            }))
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for story {story_id}: {e}")
            raise
    
    async def disconnect(self, websocket: WebSocket, story_id: str):
        """
        Remove WebSocket connection and clean up subscriptions
        
        Args:
            websocket: The WebSocket connection
            story_id: The story ID
        """
        try:
            if story_id in self.active_connections:
                self.active_connections[story_id].discard(websocket)
                
                # If no more connections for this story, unsubscribe
                if not self.active_connections[story_id]:
                    await self.pubsub.unsubscribe(f"story:{story_id}")
                    del self.active_connections[story_id]
                    logger.info(f"Unsubscribed from story:{story_id} - no active connections")
                
            logger.info(f"WebSocket disconnected for story {story_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket for story {story_id}: {e}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast_to_story(self, story_id: str, message: dict):
        """
        Broadcast a message to all WebSocket connections for a story
        
        Args:
            story_id: The story ID
            message: Message dictionary to send
        """
        if story_id not in self.active_connections:
            return
        
        # Create a copy of connections to avoid modification during iteration
        connections = self.active_connections[story_id].copy()
        message_text = json.dumps(message)
        
        # Send to all connections, removing any that are closed
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_text(message_text)
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected WebSocket connections
        for websocket in disconnected:
            await self.disconnect(websocket, story_id)
    
    async def _redis_listener(self):
        """
        Background task that listens for Redis pub/sub messages and broadcasts them
        """
        try:
            logger.info("Starting Redis listener for WebSocket broadcasts")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse the message
                        data = json.loads(message["data"])
                        story_id = data.get("story_id")
                        
                        if story_id and story_id in self.active_connections:
                            # Broadcast to all WebSocket connections for this story
                            await self.broadcast_to_story(story_id, data)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                        
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
        finally:
            logger.info("Redis listener stopped")
    
    async def handle_websocket_communication(self, websocket: WebSocket, story_id: str):
        """
        Handle the full lifecycle of a WebSocket connection
        
        Args:
            websocket: The WebSocket connection
            story_id: The story ID
        """
        try:
            # Connect the WebSocket
            await self.connect(websocket, story_id)
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for messages from client (heartbeats, etc.)
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                        message_type = message.get("type")
                        
                        if message_type == "ping":
                            # Respond to ping with pong
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "timestamp": message.get("timestamp")
                            }))
                        elif message_type == "subscribe_updates":
                            # Confirm subscription
                            await websocket.send_text(json.dumps({
                                "type": "subscription_confirmed",
                                "story_id": story_id
                            }))
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message from WebSocket: {data}")
                        
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for story {story_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in WebSocket communication: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket handler error for story {story_id}: {e}")
        finally:
            # Clean up connection
            await self.disconnect(websocket, story_id)
    
    async def cleanup(self):
        """Clean up resources when shutting down"""
        try:
            if self.redis_listener_task:
                self.redis_listener_task.cancel()
                
            if self.pubsub:
                await self.pubsub.close()
                
            if self.redis_client:
                await self.redis_client.close()
                
            logger.info("WebSocket manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during WebSocket manager cleanup: {e}")


# Global WebSocket manager instance
manager = WebSocketManager()