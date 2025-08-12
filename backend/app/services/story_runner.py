import logging
import asyncio
from typing import Dict, Any
from app.services.celery_app import celery_app
from app.db.supabase_handler import SupabaseHandler
from app.websocket.callback import RedisStreamCallbackHandler
from agent.graph import get_compiled_graph, initialize_story_workflow

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def run_story_generation_task(self, story_id: str):
    """
    Celery task to run the story generation workflow
    
    Args:
        story_id: The ID of the story to generate
        
    Returns:
        Dictionary with task results
    """
    try:
        logger.info(f"Starting story generation task for story {story_id}")
        
        # Create async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async story generation
            result = loop.run_until_complete(_run_story_generation_async(story_id))
            logger.info(f"Story generation completed for story {story_id}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Story generation task failed for {story_id}: {e}")
        
        # Retry if within retry limit
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying story generation task for {story_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        else:
            # Max retries reached, mark as failed
            logger.error(f"Max retries reached for story {story_id}, marking as failed")
            return {"status": "failed", "error": str(e), "story_id": story_id}


async def _run_story_generation_async(story_id: str) -> Dict[str, Any]:
    """
    Async function to run the story generation workflow
    
    Args:
        story_id: The story ID
        
    Returns:
        Dictionary with results
    """
    supabase_handler = SupabaseHandler()
    
    try:
        # Get story data from Supabase
        story_query = """
        SELECT s.*, ss.* FROM stories s 
        LEFT JOIN story_sessions ss ON s.id = ss.id 
        WHERE s.id = $1
        """
        
        # Get story details from Supabase (simplified approach)
        response = supabase_handler.client.table("story_sessions")\
            .select("*")\
            .eq("id", story_id)\
            .execute()
        
        if not response.data:
            raise ValueError(f"Story {story_id} not found")
        
        story_data = response.data[0]
        
        # Initialize callback handler for real-time updates
        callback_handler = RedisStreamCallbackHandler(story_id)
        
        # Get or initialize agent state
        control_state = story_data.get("control_state", {})
        
        if control_state.get("system_status") == "INITIALIZING":
            # First run - initialize the workflow
            logger.info(f"Initializing new workflow for story {story_id}")
            
            agent_state = initialize_story_workflow(
                story_id=story_id,
                title=story_data["title"],
                prompt=story_data["initial_prompt"],
                genres=story_data["genres"]
            )
        else:
            # Resuming existing workflow
            logger.info(f"Resuming workflow for story {story_id}")
            
            agent_state = {
                "story_id": story_id,
                "system_status": control_state.get("system_status", "READY"),
                "agent_question": control_state.get("agent_question"),
                "deviation_proposal": control_state.get("deviation_proposal"),
                "user_feedback": control_state.get("user_feedback"),
                "working_document": control_state.get("working_document"),
                "task_queue": control_state.get("task_queue", []),
                "checkpoint_path": f"/tmp/story_{story_id}_checkpoint.json",
                "current_scene_id": control_state.get("current_scene_id"),
                "messages": control_state.get("messages", [])
            }
        
        # Get compiled graph
        graph = get_compiled_graph()
        
        # Configuration for the graph execution
        config = {
            "callbacks": [callback_handler],
            "configurable": {
                "thread_id": story_id,
                "checkpoint_ns": "story_generation"
            }
        }
        
        # Run the graph workflow
        logger.info(f"Starting graph execution for story {story_id}")
        
        final_state = None
        step_count = 0
        
        # Stream through the graph execution
        async for state in graph.astream(agent_state, config=config):
            step_count += 1
            logger.info(f"Step {step_count} completed for story {story_id}")
            
            # Update Supabase with current state periodically
            if step_count % 3 == 0:  # Every 3 steps
                await _update_story_state(supabase_handler, story_id, state)
            
            final_state = state
            
            # Check for interruption points
            current_status = state.get("system_status", "")
            if "AWAITING" in current_status:
                logger.info(f"Workflow paused at {current_status} for story {story_id}")
                break
        
        # Final state update
        if final_state:
            await _update_story_state(supabase_handler, story_id, final_state)
        
        # Update timestamp
        await supabase_handler.update_story_timestamp(story_id)
        
        logger.info(f"Story generation workflow completed for {story_id} after {step_count} steps")
        
        return {
            "status": "completed",
            "story_id": story_id,
            "final_status": final_state.get("system_status") if final_state else "unknown",
            "steps_executed": step_count
        }
        
    except Exception as e:
        logger.error(f"Error in story generation for {story_id}: {e}")
        
        # Update story with error status
        try:
            error_state = {
                "system_status": "ERROR",
                "error_message": str(e),
                "agent_question": None,
                "deviation_proposal": None
            }
            await supabase_handler.update_story_control_state(story_id, error_state)
        except Exception as update_error:
            logger.error(f"Failed to update error status for {story_id}: {update_error}")
        
        raise


async def _update_story_state(
    supabase_handler: SupabaseHandler, 
    story_id: str, 
    state: Dict[str, Any]
) -> bool:
    """
    Update the story's control state in Supabase
    
    Args:
        supabase_handler: The Supabase handler instance
        story_id: The story ID
        state: The current agent state
        
    Returns:
        True if successful
    """
    try:
        # Extract relevant control state
        control_state = {
            "system_status": state.get("system_status"),
            "agent_question": state.get("agent_question"), 
            "deviation_proposal": state.get("deviation_proposal"),
            "user_feedback": state.get("user_feedback"),
            "working_document": state.get("working_document"),
            "task_queue": state.get("task_queue", []),
            "current_scene_id": state.get("current_scene_id"),
            "messages": state.get("messages", [])[-10:]  # Keep last 10 messages
        }
        
        # Remove None values
        control_state = {k: v for k, v in control_state.items() if v is not None}
        
        await supabase_handler.update_story_control_state(story_id, control_state)
        return True
        
    except Exception as e:
        logger.error(f"Failed to update story state for {story_id}: {e}")
        return False