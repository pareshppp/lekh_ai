import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.tools.knowledge_graph import Neo4jTool

logger = logging.getLogger(__name__)


class BrainstormerAgent:
    def __init__(self, llm: ChatOpenAI, neo4j_tool: Neo4jTool):
        self.llm = llm
        self.neo4j_tool = neo4j_tool
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Brainstormer Agent, responsible for developing the core concept of a story.
            
Given a user prompt and genres, you should:
1. Research relevant tropes and themes for the genres
2. Generate a compelling logline
3. Identify 2-3 core themes
4. Create stubs for 3-5 main characters with basic details
5. Create stubs for 2-4 key locations

Be creative and ensure all elements work together cohesively."""),
            ("user", "Prompt: {prompt}\nGenres: {genres}\n\nDevelop the core concept for this story.")
        ])
    
    def run(self, state: AgentState) -> Dict[str, Any]:
        try:
            story_id = state["story_id"]
            logger.info(f"Brainstormer starting for story {story_id}")
            
            # Get story details from Neo4j
            story_query = """
            MATCH (s:Story {story_id: $story_id})
            RETURN s.prompt as prompt, s.genres as genres, s.title as title
            """
            story_result = self.neo4j_tool.query(story_query, {"story_id": story_id})
            if not story_result:
                raise ValueError(f"Story {story_id} not found")
            
            story_data = story_result[0]
            
            # Generate core concept
            response = self.llm.invoke(self.prompt.format_messages(
                prompt=story_data["prompt"],
                genres=", ".join(story_data["genres"])
            ))
            
            concept_text = response.content
            logger.info(f"Generated concept: {concept_text[:100]}...")
            
            # Parse and structure the response (simplified - in practice would use structured output)
            themes = self._extract_themes(concept_text)
            characters = self._extract_characters(concept_text)
            locations = self._extract_locations(concept_text)
            
            # Add to knowledge graph
            for theme in themes:
                self.neo4j_tool.add_theme(story_id, theme["name"], theme["description"])
            
            for character in characters:
                self.neo4j_tool.add_character(story_id, character["name"], character)
            
            for location in locations:
                self.neo4j_tool.add_location(
                    story_id, 
                    location["name"], 
                    location["description"], 
                    location.get("atmosphere", "")
                )
            
            return {
                "system_status": "AWAITING_USER_APPROVAL_FOR_CONCEPT",
                "messages": state["messages"] + [{
                    "type": "agent_step",
                    "agent": "Brainstormer",
                    "content": f"Generated core concept with {len(themes)} themes, {len(characters)} characters, and {len(locations)} locations.",
                    "details": concept_text,
                    "timestamp": None
                }]
            }
            
        except Exception as e:
            logger.error(f"Brainstormer error: {e}")
            return {
                "system_status": "ERROR",
                "messages": state["messages"] + [{
                    "type": "error",
                    "content": f"Brainstormer failed: {str(e)}",
                    "timestamp": None
                }]
            }
    
    def _extract_themes(self, text: str) -> list[Dict[str, str]]:
        # Simplified theme extraction - in practice would use more sophisticated parsing
        return [
            {"name": "Love vs. Duty", "description": "The conflict between personal desires and obligations"},
            {"name": "Redemption", "description": "Characters seeking to atone for past mistakes"}
        ]
    
    def _extract_characters(self, text: str) -> list[Dict[str, Any]]:
        # Simplified character extraction
        return [
            {
                "name": "Protagonist",
                "backstory": "A young person with a mysterious past",
                "motivation": "To uncover the truth about their origins",
                "fears": "Being rejected by those they care about",
                "personality_traits": ["brave", "curious", "stubborn"],
                "physical_description": "Average height with distinctive eyes",
                "character_arc_summary": "Goes from naive to wise through trials"
            }
        ]
    
    def _extract_locations(self, text: str) -> list[Dict[str, str]]:
        # Simplified location extraction
        return [
            {
                "name": "The Academy",
                "description": "A prestigious institution shrouded in secrets",
                "atmosphere": "mysterious and grand"
            }
        ]