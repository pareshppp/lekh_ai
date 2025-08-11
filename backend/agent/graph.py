import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
import os

from .state import AgentState, DeviationProposal
from .agents.brainstormer import BrainstormerAgent
from .agents.architect import ArchitectAgent  
from .agents.character_smith import CharacterSmithAgent
from .agents.prose_weaver import ProseWeaverAgent
from .tools.knowledge_graph import Neo4jTool
from .tools.user_interaction import process_user_feedback

logger = logging.getLogger(__name__)


def create_narrative_graph() -> StateGraph:
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7
    )
    
    # Initialize Neo4j tool
    neo4j_tool = Neo4jTool()
    
    # Initialize agents
    brainstormer = BrainstormerAgent(llm, neo4j_tool)
    architect = ArchitectAgent(llm, neo4j_tool)
    character_smith = CharacterSmithAgent(llm, neo4j_tool)
    prose_weaver = ProseWeaverAgent(llm, neo4j_tool)
    
    # Create the state graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("brainstormer", lambda state: brainstormer.run(state))
    workflow.add_node("architect", lambda state: architect.run(state))
    workflow.add_node("character_smith", lambda state: character_smith.run(state))
    workflow.add_node("prose_weaver", lambda state: prose_weaver.run(state))
    workflow.add_node("user_approval", user_approval_node)
    workflow.add_node("user_clarification", user_clarification_node)
    workflow.add_node("deviation_review", deviation_review_node)
    workflow.add_node("supervisor", supervisor_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "brainstormer": "brainstormer",
            "architect": "architect", 
            "character_smith": "character_smith",
            "prose_weaver": "prose_weaver",
            "user_approval": "user_approval",
            "user_clarification": "user_clarification",
            "deviation_review": "deviation_review",
            "end": END
        }
    )
    
    # Add edges back to supervisor from agents
    workflow.add_edge("brainstormer", "supervisor")
    workflow.add_edge("architect", "supervisor")
    workflow.add_edge("character_smith", "supervisor")
    workflow.add_edge("prose_weaver", "supervisor")
    workflow.add_edge("user_approval", "supervisor")
    workflow.add_edge("user_clarification", "supervisor")
    workflow.add_edge("deviation_review", "supervisor")
    
    return workflow


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """Central routing logic based on system status"""
    status = state.get("system_status", "INITIALIZING")
    logger.info(f"Supervisor routing for status: {status}")
    
    return {"messages": state["messages"] + [{
        "type": "system",
        "content": f"Supervisor processing status: {status}",
        "timestamp": None
    }]}


def route_from_supervisor(state: AgentState) -> str:
    """Route to appropriate node based on system status"""
    status = state.get("system_status", "INITIALIZING")
    
    # Human-in-the-loop routing
    if "AWAITING_USER_APPROVAL" in status:
        return "user_approval"
    elif status == "AWAITING_USER_CLARIFICATION":
        return "user_clarification"  
    elif status == "AWAITING_DEVIATION_APPROVAL":
        return "deviation_review"
    
    # Agent routing based on workflow stage
    elif status == "INITIALIZING":
        return "brainstormer"
    elif status == "CONCEPT_APPROVED":
        return "character_smith"
    elif status == "CHARACTERS_APPROVED":
        # Add architect task to generate arcs
        state["task_queue"] = [{"task": "generate_arcs"}]
        return "architect"
    elif status == "ARCS_APPROVED":
        return "architect"  # Will process chapter generation tasks
    elif status == "CHAPTERS_APPROVED" or status == "SCENES_APPROVED":
        return "architect"  # Will process scene generation tasks  
    elif status == "READY_FOR_WRITING" or status == "SCENE_COMPLETED":
        return "prose_weaver"
    elif status == "WRITING_COMPLETE":
        return "end"
    elif status == "ERROR":
        return "end"
    
    # Default case
    logger.warning(f"Unknown status: {status}, ending workflow")
    return "end"


def user_approval_node(state: AgentState) -> Dict[str, Any]:
    """Handle user approval workflow"""
    logger.info("Waiting for user approval")
    
    # In a real implementation, this would pause and wait for user input
    # For now, we'll simulate approval
    status = state.get("system_status", "")
    
    if "CONCEPT" in status:
        new_status = "CONCEPT_APPROVED"
    elif "CHARACTERS" in status:
        new_status = "CHARACTERS_APPROVED"
    elif "ARCS" in status:
        new_status = "ARCS_APPROVED"
    elif "CHAPTERS" in status:
        new_status = "CHAPTERS_APPROVED"
    elif "SCENES" in status:
        new_status = "SCENES_APPROVED"
    else:
        new_status = "APPROVED"
    
    return {
        "system_status": new_status,
        "messages": state["messages"] + [{
            "type": "user_approval",
            "content": f"User approved: {status}",
            "timestamp": None
        }]
    }


def user_clarification_node(state: AgentState) -> Dict[str, Any]:
    """Handle user clarification requests"""
    logger.info("Waiting for user clarification")
    
    # In a real implementation, this would wait for user response
    # For now, simulate a response
    question = state.get("agent_question", "")
    simulated_response = "User provided clarification about character backgrounds and motivations."
    
    return process_user_feedback(state, simulated_response)


def deviation_review_node(state: AgentState) -> Dict[str, Any]:
    """Handle deviation proposal reviews"""  
    logger.info("Reviewing deviation proposal")
    
    proposal = state.get("deviation_proposal")
    if not proposal:
        return {"system_status": "ERROR", "messages": state["messages"] + [{"type": "error", "content": "No deviation proposal found"}]}
    
    # In a real implementation, user would review and decide
    # For now, simulate approval
    return {
        "system_status": "DEVIATION_APPROVED",
        "deviation_proposal": None,
        "messages": state["messages"] + [{
            "type": "deviation_approved",
            "content": f"Deviation approved for scene {proposal.original_scene_id}",
            "timestamp": None
        }]
    }


def get_compiled_graph():
    """Get the compiled graph with memory saver"""
    workflow = create_narrative_graph()
    memory = MemorySaver()
    
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["user_approval", "user_clarification", "deviation_review"]
    )


# Helper function to initialize a new story workflow
def initialize_story_workflow(story_id: str, title: str, prompt: str, genres: List[str]) -> AgentState:
    """Initialize the agent state for a new story"""
    
    # Create story node in Neo4j
    neo4j_tool = Neo4jTool()
    neo4j_tool.create_story_node(story_id, title, prompt, genres)
    
    return {
        "story_id": story_id,
        "system_status": "INITIALIZING",
        "agent_question": None,
        "deviation_proposal": None,
        "user_feedback": None,
        "working_document": None,
        "task_queue": [],
        "checkpoint_path": f"/tmp/story_{story_id}_checkpoint.json",
        "current_scene_id": None,
        "messages": [{
            "type": "system",
            "content": f"Initialized story workflow for '{title}'",
            "timestamp": None
        }]
    }