Of course. Here is the finalized and full agentic plan for the "Narrative Knowledge Weaver." This document is designed to be a comprehensive blueprint for a coding agent to generate the required codebase.

---

### **Final Plan: The "Narrative Knowledge Weaver" System**

#### **I. High-Level System Objective**

To create a collaborative, multi-agent system using LangGraph for generating coherent, novel-length stories. The system will take a user prompt and genres, then iteratively build the story through hierarchical outlining and scene-by-scene generation. It features a Knowledge Graph as its central memory, a robust human-in-the-loop protocol for approvals and edits, and allows agents to proactively ask clarifying questions and propose creative deviations.

#### **II. Core Technology Stack & Assumptions**

*   **Language:** Python 3.10+
*   **Framework:** LangChain & LangGraph
*   **Data Models:** Pydantic for state management.
*   **Database:** A Graph Database. The design will use Cypher query syntax, assuming a **Neo4j** backend. The implementation should be database-agnostic where possible by using a wrapper class.
*   **LLMs:** The system will use one or more LLMs. The specific model is configurable, but agents are designed assuming a highly capable instruction-following model.

#### **III. Central Data Structures**

**A. The Knowledge Graph (KG) Schema**

This is the permanent, durable memory of the story.

*   **Node Types:**
    *   `Story`: The root node for the entire project. Properties: `title`, `prompt`, `genres`.
    *   `Theme`: Properties: `name`, `description`.
    *   `Character`: Properties: `name`, `backstory`, `motivation`, `fears`, `personality_traits`, `physical_description`, `character_arc_summary`.
    *   `Location`: Properties: `name`, `description`, `atmosphere`, `historical_significance`.
    *   `Item`: Properties: `name`, `description`, `abilities`, `history`.
    *   `Lore`: A piece of world-building info. Properties: `title`, `content`.
    *   `Arc`: Structural element. Properties: `arc_title`, `summary`.
    *   `Chapter`: Structural element. Properties: `chapter_number`, `summary`.
    *   `Scene`: The smallest structural unit. Properties: `scene_id` (e.g., "3.2" for Chapter 3, Scene 2), `beat_sheet`, `prose_content` (text), `status` ('outlined', 'written', 'finalized').

*   **Relationship (Edge) Types:**
    *   `HAS_THEME`: (`Story`) -> (`Theme`)
    *   `CONTAINS`: (`Story`) -> (`Character` | `Location` | `Item` | `Lore` | `Arc`)
    *   `PART_OF`: (`Chapter`) -> (`Arc`); (`Scene`) -> (`Chapter`)
    *   `PRECEDES`: (`Scene`) -> (`Scene`) // To maintain chronological order
    *   `INTERACTS_WITH`: (`Character`) -> (`Character`). Properties: `relationship_type` ('friendly', 'rival', 'family', etc.).
    *   `APPEARS_IN`: (`Character`) -> (`Scene`)
    *   `LOCATED_IN`: (`Scene`) -> (`Location`)
    *   `POSSESSES`: (`Character`) -> (`Item`)
    *   `HAS_GOAL_IN`: (`Character`) -> (`Scene`). Properties: `goal_description`.

**B. The `ControlState` (Pydantic Model)**

This is the ephemeral state object passed between nodes in the LangGraph. It manages the *workflow*, not the story content.

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class DeviationProposal(BaseModel):
    original_scene_id: str
    reasoning: str
    new_beat_sheet: str
    prose_draft: Optional[str] = None # Used by Plot Doctor initially

class ControlState(BaseModel):
    # Core Project Info
    story_node_id: str # ID of the root Story node in the KG
    db_connection_info: Dict[str, Any]

    # Workflow Management
    system_status: str # e.g., "AWAITING_USER_APPROVAL_FOR_ARCS"
    task_queue: List[Dict[str, Any]] = Field(default_factory=list) # e.g., [{'agent': 'Architect', 'task': 'generate_chapters'}]
    
    # Human Interaction Payloads
    agent_question: Optional[str] = None
    deviation_proposal: Optional[DeviationProposal] = None
    user_feedback: Optional[str] = None

    # In-Progress Working Document for the Writer's Room
    working_document: Optional[Dict[str, Any]] = None # Holds the 'SceneBrief'
    
    # Pause/Resume Checkpoint Path
    checkpoint_path: str
```

#### **IV. Core Agent Tools**

These tools must be implemented and made available to the agents. They should interact with a central `GraphAPI` wrapper class.

*   `query_graph(query: str) -> List[Dict]`: Executes a read-only Cypher query.
*   `write_to_graph(query: str)`: Executes a write Cypher query.
*   `ask_user_question(question: str)`: **Action:** Sets `system_status` to `AWAITING_USER_CLARIFICATION` and populates `agent_question`. Halts agent execution.
*   `propose_outline_deviation(reasoning: str, new_beat_sheet: str, scene_id: str)`: **Action:** Sets `system_status` to `AWAITING_DEVIATION_APPROVAL` and populates `deviation_proposal`. Used by the `Plot Doctor`.

#### **V. The Main Agentic Workflow (The Supervising LangGraph)**

This graph orchestrates the high-level planning and writing process.

1.  **START**: Initialize `ControlState` from user prompt or checkpoint file. Create the root `Story` node in the KG.
2.  **Brainstormer Agent**:
    *   **Purpose**: Develops the core concept.
    *   **Prompt**: Given prompt and genres, research tropes, and generate a logline, core themes, and stubs for main characters/locations.
    *   **Action**: Writes `Theme`, `Character`, and `Location` nodes to the KG.
    *   **Next**: Transition to `UserApprovalNode`.
3.  **Architect Agent**:
    *   **Purpose**: Builds the story skeleton hierarchically.
    *   **Process**: Is called multiple times. First for Arcs, then Chapters, then Scenes.
    *   **Action**: In each run, it queries the KG for the higher-level plan and writes the next level of nodes (`Arc`, `Chapter`, `Scene`) and their `PART_OF` relationships.
    *   **Next**: Transitions to `UserApprovalNode` after each level of outlining is complete.
4.  **Character Smith & World Builder Agents**:
    *   **Purpose**: Fleshes out the details of characters and the world.
    *   **Process**: Runs after the initial concept is approved. Reads the stubs from the KG.
    *   **Action**: Updates the properties of `Character`, `Location`, `Item`, and `Lore` nodes with detailed information. Can use `ask_user_question` for ambiguity.
    *   **Next**: Transition to `UserApprovalNode`.
5.  **UserApprovalNode (Human-in-the-Loop)**:
    *   **Purpose**: Pauses the graph for user review, editing, and approval.
    *   **Process**: Presents the newly generated plan (e.g., Arc outlines) to the user. Waits for input ("approve" or text edits). Updates the KG with any edits.
    *   **Next**: Transitions back to the main Supervisor router.
6.  **Supervisor & Conditional Router**:
    *   **Purpose**: The central logic of the graph. It inspects `system_status` to decide the next step.
    *   **Logic**:
        *   If status is `..._APPROVAL`: Go to `UserApprovalNode`.
        *   If status is `AWAITING_USER_CLARIFICATION`: Go to a `ClarificationNode` (similar to approval node).
        *   If status is `AWAITING_DEVIATION_APPROVAL`: Go to the `DeviationReviewerNode` in the Writer's Room subgraph.
        *   If the outlining is complete: Begin iterating through Scene nodes with status 'outlined' and trigger the **"Writer's Room" Subgraph** for each one.
7.  **"Writer's Room" Subgraph**: (See Section VI for details). This is a nested graph.
8.  **Continuity Editor Agent**:
    *   **Purpose**: To perform a final check after a chapter is fully written.
    *   **Process**: Queries the KG for the latest chapter's scenes and cross-references them against the entire story KG for logical consistency.
    *   **Action**: Generates a report of potential inconsistencies. Does not edit directly.
    *   **Next**: Presents the report to the user for final chapter approval.
9.  **END**: The graph finishes when all scenes are 'finalized'.

#### **VI. The "Writer's Room" Subgraph**

This is a dedicated LangGraph subgraph invoked for each scene.

1.  **Scene Architect Agent**:
    *   **Purpose**: Gathers context and creates a `SceneBrief`.
    *   **Action**: Queries the KG for all relevant info for a given `scene_id`. Puts this structured brief into the `ControlState.working_document`.
    *   **Next**: `Plot Doctor`.
2.  **Plot Doctor Agent**:
    *   **Purpose**: Reviews the plan for creative soundness.
    *   **Prompt**: "Critique this scene plan. Is it dramatic? Does it serve the characters? Propose a better outline using `propose_outline_deviation` if you have one. Otherwise, approve."
    *   **Next**: A conditional router. If deviation is proposed, go to `DeviationReviewerNode`. If not, go to `Drafter`.
3.  **DeviationReviewerNode (Human-in-the-Loop)**:
    *   **Purpose**: Allows user to approve/reject/edit the `Plot Doctor`'s creative suggestion.
    *   **Process**: Presents original vs. proposed beat sheet. Updates KG if approved.
    *   **Next**: If approved, loops back to `Scene Architect` to rebuild the brief. If rejected, proceeds to `Drafter` with original plan.
4.  **Drafter Agent**:
    *   **Purpose**: Writes the main narrative prose.
    *   **Prompt**: "Using the attached brief, write the scene's action and description. Use placeholders like `[Character A argues]` for dialogue."
    *   **Action**: Adds the draft prose to the `working_document`.
    *   **Next**: `Dialogue Smith`.
5.  **Dialogue Smith Agent**:
    *   **Purpose**: Writes character-specific dialogue.
    *   **Prompt**: "Read the scene draft and character profiles. Replace placeholders with sharp, authentic dialogue that reflects each character's voice and goals."
    *   **Action**: Updates the prose in the `working_document`.
    *   **Next**: `Style Editor`.
6.  **Style Editor Agent**:
    *   **Purpose**: Polishes the final text.
    *   **Prompt**: "Review the scene. Unify the tone, polish the prose for flow and rhythm, and fix any grammatical errors. The output must be publication-ready."
    *   **Action**: Creates the final `prose_content` in the `working_document`.
    *   **Next**: `FinalizationNode`.
7.  **FinalizationNode**:
    *   **Purpose**: Commits the finished scene to the database.
    *   **Action**: Takes the final prose from `working_document`, executes a `write_to_graph` query to update the `Scene` node's `prose_content`, and sets its status to 'written'.
    *   **Next**: Exits the subgraph, returning control to the main Supervisor.

#### **VII. Implementation Notes for the Coding Agent**

*   **GraphAPI Wrapper:** Do not let agents construct raw Cypher queries. Implement a `GraphAPI` class with methods like `get_character(name)`, `update_scene_prose(scene_id, text)`, `find_scenes_with_character(name)`. This centralizes and validates DB interactions.
*   **State Management:** Use the Pydantic `ControlState` model rigorously. Every node takes this state and returns a dictionary with the fields to be updated.
*   **Configurable HITL:** The prompts for the `UserApprovalNode` and other human interfaces should be configurable. The user should be able to set an "autonomy level" that bypasses certain approval steps (e.g., approve scenes automatically but pause for chapters).
*   **Error Handling:** Each node should be wrapped in error handling. If an agent or tool fails, the `system_status` should be updated to `ERROR`, and the state should be saved for debugging.
*   **Logging:** Implement comprehensive logging at each step, recording which agent is running, what its inputs are, and what changes it makes to the state or KG.
*   **Pause/Resume:** The `UserApprovalNode` (and any other blocking node) should first serialize the current `ControlState` to the specified `checkpoint_path` before waiting for input. The main application entry point should check if a checkpoint file exists to resume an in-progress generation. The KG acts as the durable memory for the story itself.