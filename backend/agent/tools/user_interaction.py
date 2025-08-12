import logging
from typing import Dict, Any
from agent.state import AgentState, DeviationProposal

logger = logging.getLogger(__name__)


def ask_user_question(state: AgentState, question: str) -> Dict[str, Any]:
    logger.info(f"Agent asking user question: {question}")
    return {
        "system_status": "AWAITING_USER_CLARIFICATION",
        "agent_question": question,
        "messages": state["messages"] + [{
            "type": "agent_question",
            "content": question,
            "timestamp": None  # Will be set by callback handler
        }]
    }


def propose_outline_deviation(
    state: AgentState, 
    reasoning: str, 
    new_beat_sheet: str, 
    scene_id: str,
    prose_draft: str = None
) -> Dict[str, Any]:
    logger.info(f"Agent proposing deviation for scene {scene_id}: {reasoning}")
    
    deviation = DeviationProposal(
        original_scene_id=scene_id,
        reasoning=reasoning,
        new_beat_sheet=new_beat_sheet,
        prose_draft=prose_draft
    )
    
    return {
        "system_status": "AWAITING_DEVIATION_APPROVAL",
        "deviation_proposal": deviation,
        "messages": state["messages"] + [{
            "type": "deviation_proposal",
            "content": {
                "scene_id": scene_id,
                "reasoning": reasoning,
                "new_beat_sheet": new_beat_sheet
            },
            "timestamp": None
        }]
    }


def wait_for_user_input(state: AgentState) -> Dict[str, Any]:
    logger.info("Waiting for user input")
    return {
        "system_status": "AWAITING_USER_INPUT",
        "messages": state["messages"] + [{
            "type": "system",
            "content": "Waiting for user input...",
            "timestamp": None
        }]
    }


def process_user_feedback(state: AgentState, feedback: str) -> Dict[str, Any]:
    logger.info(f"Processing user feedback: {feedback}")
    
    # Clear any pending questions or proposals
    updates = {
        "user_feedback": feedback,
        "agent_question": None,
        "deviation_proposal": None,
        "system_status": "PROCESSING_FEEDBACK",
        "messages": state["messages"] + [{
            "type": "user_feedback",
            "content": feedback,
            "timestamp": None
        }]
    }
    
    return updates