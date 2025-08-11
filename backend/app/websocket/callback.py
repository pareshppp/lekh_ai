import json
import logging
import redis
from datetime import datetime
from typing import Dict, Any, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from ..core.config import settings

logger = logging.getLogger(__name__)


class RedisStreamCallbackHandler(BaseCallbackHandler):
    """
    LangGraph callback handler that publishes updates to Redis for WebSocket streaming
    """
    
    def __init__(self, story_id: str):
        super().__init__()
        self.story_id = story_id
        self.channel = f"story:{story_id}"
        
        # Initialize Redis client
        self.redis_client = redis.from_url(
            settings.celery_broker_url,
            decode_responses=True
        )
        
    def _publish_message(self, message_type: str, content: Any, agent: str = None, details: str = None):
        """
        Publish a message to the Redis channel
        
        Args:
            message_type: Type of message (agent_step, thought, tool_call, etc.)
            content: Message content
            agent: Name of the agent (optional)
            details: Additional details (optional)
        """
        try:
            message = {
                "type": message_type,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "story_id": self.story_id
            }
            
            if agent:
                message["agent"] = agent
            if details:
                message["details"] = details
            
            # Publish to Redis channel
            self.redis_client.publish(
                self.channel,
                json.dumps(message)
            )
            
            logger.debug(f"Published {message_type} message to {self.channel}")
            
        except Exception as e:
            logger.error(f"Failed to publish message to Redis: {e}")
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        """Called when LLM starts running"""
        agent_name = kwargs.get("tags", [])
        agent_name = agent_name[0] if agent_name else "Unknown Agent"
        
        self._publish_message(
            "llm_start",
            f"{agent_name} is thinking...",
            agent=agent_name
        )
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM finishes running"""
        agent_name = kwargs.get("tags", [])
        agent_name = agent_name[0] if agent_name else "Unknown Agent"
        
        if response.generations and response.generations[0]:
            content = response.generations[0][0].text[:200] + "..." if len(response.generations[0][0].text) > 200 else response.generations[0][0].text
            
            self._publish_message(
                "llm_end",
                f"{agent_name} completed thinking",
                agent=agent_name,
                details=content
            )
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM encounters an error"""
        self._publish_message(
            "llm_error", 
            f"LLM error: {str(error)}"
        )
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain starts running"""
        chain_name = serialized.get("name", "Unknown Chain")
        
        self._publish_message(
            "chain_start",
            f"Started {chain_name}",
            agent=chain_name
        )
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain finishes running"""
        chain_name = kwargs.get("name", "Unknown Chain")
        
        self._publish_message(
            "chain_end",
            f"Completed {chain_name}",
            agent=chain_name
        )
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a chain encounters an error"""
        self._publish_message(
            "chain_error",
            f"Chain error: {str(error)}"
        )
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when a tool starts running"""
        tool_name = serialized.get("name", "Unknown Tool")
        
        self._publish_message(
            "tool_start",
            f"Using tool: {tool_name}",
            details=input_str[:100] + "..." if len(input_str) > 100 else input_str
        )
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool finishes running"""
        tool_name = kwargs.get("name", "Unknown Tool")
        
        self._publish_message(
            "tool_end",
            f"Tool {tool_name} completed",
            details=output[:100] + "..." if len(output) > 100 else output
        )
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a tool encounters an error"""
        self._publish_message(
            "tool_error",
            f"Tool error: {str(error)}"
        )
    
    def on_text(self, text: str, **kwargs: Any) -> None:
        """Called when arbitrary text is processed"""
        # Only log significant text events
        if len(text.strip()) > 10:
            self._publish_message(
                "text",
                text[:200] + "..." if len(text) > 200 else text
            )
    
    def on_agent_action(self, action, **kwargs: Any) -> None:
        """Called when an agent takes an action"""
        self._publish_message(
            "agent_action",
            f"Agent taking action: {action.tool}",
            details=str(action.tool_input)[:100]
        )
    
    def on_agent_finish(self, finish, **kwargs: Any) -> None:
        """Called when an agent finishes"""
        self._publish_message(
            "agent_finish",
            "Agent completed its task",
            details=str(finish.return_values)[:200]
        )