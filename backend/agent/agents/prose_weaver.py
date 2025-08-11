import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from ..state import AgentState, SceneBrief
from ..tools.knowledge_graph import Neo4jTool
from ..tools.user_interaction import propose_outline_deviation

logger = logging.getLogger(__name__)


class ProseWeaverAgent:
    """The Writer's Room subgraph agents combined into one for simplicity"""
    
    def __init__(self, llm: ChatOpenAI, neo4j_tool: Neo4jTool):
        self.llm = llm
        self.neo4j_tool = neo4j_tool
        
        # Scene Architect prompts
        self.scene_architect_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Scene Architect, gathering context for scene writing.
            
Create a comprehensive SceneBrief that includes:
1. The scene's beat sheet and objectives
2. All characters appearing in the scene
3. Location details and atmosphere
4. Relevant context from previous scenes
5. Story themes that should be reflected

Be thorough - this brief will guide the entire scene writing process."""),
            ("user", "Scene ID: {scene_id}\nStory Context: {story_context}\n\nCreate a comprehensive scene brief.")
        ])
        
        # Plot Doctor prompts
        self.plot_doctor_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Plot Doctor, responsible for creative review.
            
Review this scene plan critically:
1. Is it dramatically compelling?
2. Does it serve character development?
3. Does it advance the plot meaningfully?
4. Are there missed opportunities?

If you see a better approach, propose a deviation with your reasoning.
Otherwise, approve the current plan."""),
            ("user", "Scene Brief: {scene_brief}\n\nReview this scene plan and provide feedback or propose improvements.")
        ])
        
        # Prose writing prompts
        self.drafter_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Drafter, writing narrative prose.
            
Write the main narrative for this scene:
1. Set the atmosphere and describe the setting
2. Show character actions and reactions
3. Use placeholders like [Character argues] for dialogue
4. Focus on vivid, engaging prose
5. Maintain story themes and character consistency

Write in third person past tense. Be descriptive but not overwrought."""),
            ("user", "Scene Brief: {scene_brief}\n\nWrite the narrative prose for this scene.")
        ])
        
        self.dialogue_smith_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Dialogue Smith, crafting authentic dialogue.
            
Replace dialogue placeholders with natural, character-specific dialogue:
1. Each character should have a distinct voice
2. Dialogue should reveal character and advance plot
3. Include subtext and conflict where appropriate
4. Keep exchanges dynamic and realistic

Consider each character's background, personality, and goals in the scene."""),
            ("user", "Scene Draft: {scene_draft}\nCharacter Profiles: {character_profiles}\n\nAdd dialogue to complete the scene.")
        ])
        
        self.style_editor_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Style Editor, polishing the final prose.
            
Polish this scene to publication quality:
1. Ensure consistent tone and style
2. Improve flow and rhythm
3. Fix any grammatical errors
4. Enhance word choice and imagery
5. Maintain the author's voice

The result should be ready for readers."""),
            ("user", "Scene Draft: {scene_draft}\n\nPolish this scene to final quality.")
        ])
    
    def run(self, state: AgentState) -> Dict[str, Any]:
        try:
            story_id = state["story_id"]
            current_scene_id = state.get("current_scene_id")
            
            if not current_scene_id:
                # Get next scene to write
                scenes_to_write = self.neo4j_tool.get_scenes_with_status(story_id, "outlined")
                if not scenes_to_write:
                    return {
                        "system_status": "WRITING_COMPLETE",
                        "messages": state["messages"] + [{
                            "type": "system",
                            "content": "All scenes have been written!",
                            "timestamp": None
                        }]
                    }
                current_scene_id = scenes_to_write[0]
            
            logger.info(f"Prose Weaver working on scene {current_scene_id}")
            
            # Step 1: Scene Architect - Create scene brief
            scene_brief = self._create_scene_brief(story_id, current_scene_id)
            
            # Step 2: Plot Doctor - Review and potentially propose deviations
            plot_review = self._review_scene_plan(scene_brief)
            if plot_review.get("propose_deviation"):
                return propose_outline_deviation(
                    state,
                    plot_review["reasoning"],
                    plot_review["new_beat_sheet"],
                    current_scene_id
                )
            
            # Step 3: Draft the scene prose
            scene_draft = self._draft_scene(scene_brief)
            
            # Step 4: Add dialogue
            scene_with_dialogue = self._add_dialogue(scene_draft, scene_brief)
            
            # Step 5: Style editing
            final_scene = self._polish_prose(scene_with_dialogue)
            
            # Step 6: Save to knowledge graph
            self.neo4j_tool.update_scene_prose(story_id, current_scene_id, final_scene, "written")
            
            # Get next scene for continuing the work
            remaining_scenes = self.neo4j_tool.get_scenes_with_status(story_id, "outlined")
            next_scene_id = remaining_scenes[0] if remaining_scenes else None
            
            return {
                "system_status": "SCENE_COMPLETED" if next_scene_id else "WRITING_COMPLETE",
                "current_scene_id": next_scene_id,
                "messages": state["messages"] + [{
                    "type": "agent_step",
                    "agent": "Prose Weaver",
                    "content": f"Completed scene {current_scene_id}. {'Working on next scene.' if next_scene_id else 'All scenes complete!'}",
                    "details": final_scene[:200] + "...",
                    "timestamp": None
                }]
            }
            
        except Exception as e:
            logger.error(f"Prose Weaver error: {e}")
            return {
                "system_status": "ERROR",
                "messages": state["messages"] + [{
                    "type": "error",
                    "content": f"Prose Weaver failed: {str(e)}",
                    "timestamp": None
                }]
            }
    
    def _create_scene_brief(self, story_id: str, scene_id: str) -> Dict[str, Any]:
        # Get comprehensive scene context
        context = self.neo4j_tool.get_scene_context(story_id, scene_id)
        
        # Get additional story context
        story_context = self._get_story_context(story_id)
        
        response = self.llm.invoke(self.scene_architect_prompt.format_messages(
            scene_id=scene_id,
            story_context=str({**context, **story_context})
        ))
        
        # Create structured scene brief
        return {
            "scene_id": scene_id,
            "beat_sheet": context.get("scene", {}).get("beat_sheet", ""),
            "characters": context.get("characters", []),
            "location": context.get("location"),
            "previous_scenes": context.get("previous_scenes", []),
            "story_context": story_context,
            "architect_notes": response.content
        }
    
    def _review_scene_plan(self, scene_brief: Dict[str, Any]) -> Dict[str, Any]:
        response = self.llm.invoke(self.plot_doctor_prompt.format_messages(
            scene_brief=str(scene_brief)
        ))
        
        review_text = response.content.lower()
        
        # Simple check for deviation proposals
        if any(phrase in review_text for phrase in ["propose", "suggest", "better approach", "improvement"]):
            return {
                "propose_deviation": True,
                "reasoning": "Plot Doctor suggests improvements to scene structure and dramatic impact",
                "new_beat_sheet": "Revised beat sheet with enhanced dramatic tension and character development opportunities"
            }
        
        return {"propose_deviation": False}
    
    def _draft_scene(self, scene_brief: Dict[str, Any]) -> str:
        response = self.llm.invoke(self.drafter_prompt.format_messages(
            scene_brief=str(scene_brief)
        ))
        return response.content
    
    def _add_dialogue(self, scene_draft: str, scene_brief: Dict[str, Any]) -> str:
        character_profiles = "\n".join([
            f"- {char.get('name', 'Unknown')}: {char.get('personality_traits', [])} - {char.get('motivation', 'Unknown motivation')}"
            for char in scene_brief.get("characters", [])
        ])
        
        response = self.llm.invoke(self.dialogue_smith_prompt.format_messages(
            scene_draft=scene_draft,
            character_profiles=character_profiles
        ))
        return response.content
    
    def _polish_prose(self, scene_draft: str) -> str:
        response = self.llm.invoke(self.style_editor_prompt.format_messages(
            scene_draft=scene_draft
        ))
        return response.content
    
    def _get_story_context(self, story_id: str) -> Dict[str, Any]:
        # Get themes
        themes_query = """
        MATCH (t:Theme {story_id: $story_id})
        RETURN collect({name: t.name, description: t.description}) as themes
        """
        themes_result = self.neo4j_tool.query(themes_query, {"story_id": story_id})
        
        # Get story details
        story_query = """
        MATCH (s:Story {story_id: $story_id})
        RETURN s.prompt as prompt, s.genres as genres, s.title as title
        """
        story_result = self.neo4j_tool.query(story_query, {"story_id": story_id})
        
        return {
            "themes": themes_result[0]["themes"] if themes_result else [],
            "prompt": story_result[0]["prompt"] if story_result else "",
            "genres": story_result[0]["genres"] if story_result else [],
            "title": story_result[0]["title"] if story_result else ""
        }