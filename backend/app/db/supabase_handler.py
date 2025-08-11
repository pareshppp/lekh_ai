import asyncio
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from ..core.config import settings

logger = logging.getLogger(__name__)


class SupabaseHandler:
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    
    async def get_user_stories(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all stories for a user
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of story dictionaries
        """
        try:
            response = self.client.table("story_sessions")\
                .select("id, title, created_at, updated_at, control_state")\
                .eq("owner_id", user_id)\
                .order("updated_at", desc=True)\
                .execute()
            
            if response.data is None:
                logger.warning(f"No stories found for user {user_id}")
                return []
            
            return response.data
            
        except Exception as e:
            logger.error(f"Failed to fetch stories for user {user_id}: {e}")
            raise
    
    async def create_story(
        self,
        story_id: str,
        owner_id: str,
        title: str,
        initial_prompt: str,
        genres: List[str],
        control_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new story session
        
        Args:
            story_id: Unique story identifier
            owner_id: User ID who owns the story
            title: Story title
            initial_prompt: The initial user prompt
            genres: List of genre strings
            control_state: Initial control state for the workflow
            
        Returns:
            Created story data
        """
        try:
            story_data = {
                "id": story_id,
                "owner_id": owner_id,
                "title": title,
                "initial_prompt": initial_prompt,
                "genres": genres,
                "control_state": control_state
            }
            
            response = self.client.table("story_sessions")\
                .insert(story_data)\
                .execute()
            
            if not response.data:
                raise Exception("Failed to create story - no data returned")
            
            logger.info(f"Created story {story_id} for user {owner_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Failed to create story {story_id}: {e}")
            raise
    
    async def get_story_by_id(self, story_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a story by ID, ensuring the user owns it
        
        Args:
            story_id: The story ID
            user_id: The user ID (for ownership verification)
            
        Returns:
            Story data if found and owned by user, None otherwise
        """
        try:
            response = self.client.table("story_sessions")\
                .select("*")\
                .eq("id", story_id)\
                .eq("owner_id", user_id)\
                .execute()
            
            if not response.data:
                logger.warning(f"Story {story_id} not found for user {user_id}")
                return None
            
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Failed to fetch story {story_id}: {e}")
            raise
    
    async def update_story_control_state(
        self, 
        story_id: str, 
        control_state: Dict[str, Any]
    ) -> bool:
        """
        Update the control state of a story
        
        Args:
            story_id: The story ID
            control_state: New control state data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.table("story_sessions")\
                .update({"control_state": control_state})\
                .eq("id", story_id)\
                .execute()
            
            if not response.data:
                logger.warning(f"No story found to update: {story_id}")
                return False
            
            logger.info(f"Updated control state for story {story_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update control state for story {story_id}: {e}")
            raise
    
    async def delete_story(self, story_id: str, user_id: str) -> bool:
        """
        Delete a story (with ownership verification)
        
        Args:
            story_id: The story ID
            user_id: The user ID (for ownership verification)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.table("story_sessions")\
                .delete()\
                .eq("id", story_id)\
                .eq("owner_id", user_id)\
                .execute()
            
            if not response.data:
                logger.warning(f"Story {story_id} not found or not owned by user {user_id}")
                return False
            
            logger.info(f"Deleted story {story_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete story {story_id}: {e}")
            raise
    
    async def get_story_control_state(self, story_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current control state for a story
        
        Args:
            story_id: The story ID
            
        Returns:
            Control state data if found, None otherwise
        """
        try:
            response = self.client.table("story_sessions")\
                .select("control_state")\
                .eq("id", story_id)\
                .execute()
            
            if not response.data:
                return None
            
            return response.data[0]["control_state"]
            
        except Exception as e:
            logger.error(f"Failed to get control state for story {story_id}: {e}")
            raise
    
    async def update_story_timestamp(self, story_id: str) -> bool:
        """
        Update the updated_at timestamp for a story
        
        Args:
            story_id: The story ID
            
        Returns:
            True if successful
        """
        try:
            response = self.client.table("story_sessions")\
                .update({"updated_at": "now()"})\
                .eq("id", story_id)\
                .execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Failed to update timestamp for story {story_id}: {e}")
            return False