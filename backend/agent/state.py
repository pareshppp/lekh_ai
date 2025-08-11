from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, TypedDict


class DeviationProposal(BaseModel):
    original_scene_id: str
    reasoning: str
    new_beat_sheet: str
    prose_draft: Optional[str] = None


class ControlState(BaseModel):
    story_node_id: str
    db_connection_info: Dict[str, Any]
    system_status: str
    task_queue: List[Dict[str, Any]] = Field(default_factory=list)
    agent_question: Optional[str] = None
    deviation_proposal: Optional[DeviationProposal] = None
    user_feedback: Optional[str] = None
    working_document: Optional[Dict[str, Any]] = None
    checkpoint_path: str


class AgentState(TypedDict):
    story_id: str
    system_status: str
    agent_question: Optional[str]
    deviation_proposal: Optional[DeviationProposal]
    user_feedback: Optional[str]
    working_document: Optional[Dict[str, Any]]
    task_queue: List[Dict[str, Any]]
    checkpoint_path: str
    current_scene_id: Optional[str]
    messages: List[Dict[str, Any]]


class SceneBrief(BaseModel):
    scene_id: str
    beat_sheet: str
    characters: List[Dict[str, Any]]
    location: Optional[Dict[str, Any]]
    previous_scenes: List[str]
    story_context: Dict[str, Any]