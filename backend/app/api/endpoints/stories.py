import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user_id
from app.db.supabase_handler import SupabaseHandler
from app.services.story_runner import run_story_generation_task
from agent.tools.knowledge_graph import Neo4jTool

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
supabase_handler = SupabaseHandler()
neo4j_tool = Neo4jTool()


# Request/Response models
class CreateStoryRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1000)
    genres: List[str] = Field(..., min_items=1, max_items=5)
    title: Optional[str] = Field(None, max_length=200)


class StoryResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    system_status: str


class DeleteStoriesRequest(BaseModel):
    story_ids: List[str] = Field(..., min_items=1)


class UserInteractionRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


@router.get("/stories", response_model=List[StoryResponse])
async def get_user_stories(user_id: str = Depends(get_current_user_id)):
    """
    Fetch all stories for the authenticated user
    """
    try:
        stories = await supabase_handler.get_user_stories(user_id)
        return [
            StoryResponse(
                id=story["id"],
                title=story["title"],
                created_at=story["created_at"],
                updated_at=story["updated_at"],
                system_status=story.get("control_state", {}).get("system_status", "unknown")
            )
            for story in stories
        ]
    except Exception as e:
        logger.error(f"Failed to fetch stories for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch stories"
        )


@router.post("/stories", response_model=Dict[str, str])
async def create_story(
    request: CreateStoryRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new story and start the AI generation process
    """
    try:
        # Generate unique story ID
        story_id = str(uuid.uuid4())
        
        # Generate title if not provided
        title = request.title or f"Story from: {request.prompt[:50]}..."
        
        # Create initial control state
        initial_control_state = {
            "system_status": "INITIALIZING",
            "agent_question": None,
            "deviation_proposal": None,
            "user_feedback": None,
            "task_queue": []
        }
        
        # Create story record in Supabase
        story_data = await supabase_handler.create_story(
            story_id=story_id,
            owner_id=user_id,
            title=title,
            initial_prompt=request.prompt,
            genres=request.genres,
            control_state=initial_control_state
        )
        
        # Trigger Celery task for AI generation
        task_result = run_story_generation_task.delay(story_id=story_id)
        logger.info(f"Started story generation task {task_result.id} for story {story_id}")
        
        return {
            "story_id": story_id,
            "title": title,
            "status": "Story generation started",
            "task_id": task_result.id
        }
        
    except Exception as e:
        logger.error(f"Failed to create story for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create story"
        )


@router.delete("/stories")
async def delete_stories(
    request: DeleteStoriesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Delete one or more stories
    """
    try:
        deleted_count = 0
        errors = []
        
        for story_id in request.story_ids:
            try:
                # Verify ownership
                story = await supabase_handler.get_story_by_id(story_id, user_id)
                if not story:
                    errors.append(f"Story {story_id} not found or access denied")
                    continue
                
                # Delete from Neo4j
                neo4j_success = neo4j_tool.delete_story_nodes(story_id)
                if not neo4j_success:
                    logger.warning(f"Failed to delete Neo4j nodes for story {story_id}")
                
                # Delete from Supabase
                await supabase_handler.delete_story(story_id, user_id)
                deleted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to delete story {story_id}: {e}")
                errors.append(f"Failed to delete story {story_id}: {str(e)}")
        
        return {
            "deleted_count": deleted_count,
            "total_requested": len(request.story_ids),
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Failed to delete stories for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete stories"
        )


@router.get("/stories/{story_id}")
async def get_story_details(
    story_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get detailed information about a specific story
    """
    try:
        # Verify ownership and get story from Supabase
        story = await supabase_handler.get_story_by_id(story_id, user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        # Get story outline from Neo4j
        outline = neo4j_tool.get_story_outline(story_id)
        
        return {
            **story,
            "outline": outline
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get story details for {story_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch story details"
        )


@router.post("/stories/{story_id}/interact")
async def interact_with_story(
    story_id: str,
    request: UserInteractionRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Send a message/feedback to the AI agent for a story
    """
    try:
        # Verify ownership
        story = await supabase_handler.get_story_by_id(story_id, user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        # Update control state with user feedback
        control_state = story.get("control_state", {})
        control_state["user_feedback"] = request.message
        control_state["system_status"] = "PROCESSING_FEEDBACK"
        
        # Update in Supabase
        await supabase_handler.update_story_control_state(story_id, control_state)
        
        # Trigger continuation of the story generation process
        task_result = run_story_generation_task.delay(story_id=story_id)
        
        return {
            "message": "Feedback received and processing started",
            "task_id": task_result.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process interaction for story {story_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process interaction"
        )


@router.get("/stories/{story_id}/outline")
async def get_story_outline(
    story_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get the story's structural outline (arcs, chapters, scenes)
    """
    try:
        # Verify ownership
        story = await supabase_handler.get_story_by_id(story_id, user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        # Get outline from Neo4j
        outline = neo4j_tool.get_story_outline(story_id)
        
        return outline
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get outline for story {story_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch story outline"
        )


@router.get("/stories/{story_id}/content/{node_id}")
async def get_story_content(
    story_id: str,
    node_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get content for a specific story node (scene, character, etc.)
    """
    try:
        # Verify ownership
        story = await supabase_handler.get_story_by_id(story_id, user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        # Get node content from Neo4j
        query = """
        MATCH (n {story_id: $story_id})
        WHERE id(n) = $node_id OR n.scene_id = $node_id OR n.name = $node_id
        RETURN n
        """
        
        result = neo4j_tool.query(query, {"story_id": story_id, "node_id": node_id})
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        
        return result[0]["n"]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content for {story_id}/{node_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch content"
        )


@router.get("/stories/{story_id}/bible/{category}")
async def get_story_bible_category(
    story_id: str,
    category: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get story bible entries for a specific category (characters, locations, etc.)
    """
    try:
        # Verify ownership
        story = await supabase_handler.get_story_by_id(story_id, user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found"
            )
        
        # Get category data from Neo4j
        if category == "characters":
            data = neo4j_tool.get_characters(story_id)
        elif category == "locations":
            data = neo4j_tool.get_locations(story_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown category: {category}"
            )
        
        return {"category": category, "items": data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get {category} for story {story_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch {category}"
        )