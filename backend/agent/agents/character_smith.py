import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from ..state import AgentState
from ..tools.knowledge_graph import Neo4jTool
from ..tools.user_interaction import ask_user_question

logger = logging.getLogger(__name__)


class CharacterSmithAgent:
    def __init__(self, llm: ChatOpenAI, neo4j_tool: Neo4jTool):
        self.llm = llm
        self.neo4j_tool = neo4j_tool
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Character Smith Agent, responsible for developing rich, detailed characters.
            
Your task is to take character stubs and flesh them out with:
1. Detailed backstory that explains their motivations
2. Complex personality traits with contradictions
3. Specific fears and desires
4. Physical description that reflects their character
5. Clear character arc that serves the story themes
6. Unique voice and mannerisms

Make characters feel real and human, with flaws and growth potential.
If you need clarification about character details, ask specific questions."""),
            ("user", """Character Stub:
Name: {name}
Current Backstory: {backstory}
Current Motivation: {motivation}
Story Themes: {themes}
Story Context: {context}

Develop this character fully. If any aspect needs clarification, ask specific questions.""")
        ])
    
    def run(self, state: AgentState) -> Dict[str, Any]:
        try:
            story_id = state["story_id"]
            logger.info(f"Character Smith starting for story {story_id}")
            
            # Get character stubs that need development
            characters = self._get_character_stubs(story_id)
            
            if not characters:
                return {
                    "system_status": "CHARACTER_DEVELOPMENT_COMPLETE",
                    "messages": state["messages"] + [{
                        "type": "agent_step",
                        "agent": "Character Smith",
                        "content": "No characters need development",
                        "timestamp": None
                    }]
                }
            
            # Get story context for character development
            context = self._get_story_context(story_id)
            
            developed_characters = []
            
            for character in characters:
                logger.info(f"Developing character: {character['name']}")
                
                # Check if character needs user clarification
                if self._needs_clarification(character):
                    question = self._generate_clarification_question(character)
                    return ask_user_question(state, question)
                
                # Develop the character
                developed_char = self._develop_character(character, context)
                
                if developed_char:
                    # Update character in knowledge graph
                    self._update_character(story_id, developed_char)
                    developed_characters.append(developed_char)
            
            return {
                "system_status": "AWAITING_USER_APPROVAL_FOR_CHARACTERS",
                "messages": state["messages"] + [{
                    "type": "agent_step",
                    "agent": "Character Smith",
                    "content": f"Developed {len(developed_characters)} characters: {', '.join([c['name'] for c in developed_characters])}",
                    "details": self._format_character_details(developed_characters),
                    "timestamp": None
                }]
            }
            
        except Exception as e:
            logger.error(f"Character Smith error: {e}")
            return {
                "system_status": "ERROR",
                "messages": state["messages"] + [{
                    "type": "error", 
                    "content": f"Character Smith failed: {str(e)}",
                    "timestamp": None
                }]
            }
    
    def _get_character_stubs(self, story_id: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:Character {story_id: $story_id})
        WHERE c.backstory IS NULL OR c.backstory = "" OR length(c.backstory) < 50
        RETURN c
        """
        result = self.neo4j_tool.query(query, {"story_id": story_id})
        return [record["c"] for record in result]
    
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
        RETURN s.prompt as prompt, s.genres as genres
        """
        story_result = self.neo4j_tool.query(story_query, {"story_id": story_id})
        
        return {
            "themes": themes_result[0]["themes"] if themes_result else [],
            "prompt": story_result[0]["prompt"] if story_result else "",
            "genres": story_result[0]["genres"] if story_result else []
        }
    
    def _needs_clarification(self, character: Dict[str, Any]) -> bool:
        # Check if character has vague or minimal information
        backstory = character.get("backstory", "")
        motivation = character.get("motivation", "")
        
        vague_terms = ["mysterious", "unknown", "TBD", "to be determined", "unclear"]
        
        for term in vague_terms:
            if term.lower() in backstory.lower() or term.lower() in motivation.lower():
                return True
        
        return len(backstory) < 20 or len(motivation) < 15
    
    def _generate_clarification_question(self, character: Dict[str, Any]) -> str:
        name = character.get("name", "the character")
        backstory = character.get("backstory", "")
        motivation = character.get("motivation", "")
        
        if "mysterious" in backstory.lower():
            return f"What specific mystery surrounds {name}'s past? What event or secret defines their backstory?"
        elif len(backstory) < 20:
            return f"What is {name}'s background? Where do they come from and what shaped them?"
        elif len(motivation) < 15:
            return f"What does {name} want most in this story? What drives their actions?"
        else:
            return f"What additional details would help develop {name}'s character?"
    
    def _develop_character(self, character: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.llm.invoke(self.prompt.format_messages(
                name=character.get("name", "Unknown"),
                backstory=character.get("backstory", "To be developed"),
                motivation=character.get("motivation", "To be developed"),
                themes=self._format_themes(context["themes"]),
                context=f"Prompt: {context['prompt']}\nGenres: {', '.join(context['genres'])}"
            ))
            
            # Parse the response to extract character details
            # This is simplified - in practice would use structured output
            return self._parse_character_development(response.content, character)
            
        except Exception as e:
            logger.error(f"Error developing character {character.get('name')}: {e}")
            return None
    
    def _parse_character_development(self, response: str, original_character: Dict[str, Any]) -> Dict[str, Any]:
        # Simplified parsing - in practice would use structured output or better parsing
        return {
            "name": original_character.get("name"),
            "backstory": "A detailed backstory developed from the original stub, explaining their origins, formative experiences, and key relationships that shaped who they are today.",
            "motivation": "A clear, compelling motivation that drives their actions throughout the story and connects to the main themes.",
            "fears": "Specific fears that create internal conflict and obstacles to achieving their goals.",
            "personality_traits": ["brave", "impulsive", "loyal", "secretive"],
            "physical_description": "A vivid physical description that reflects their personality and background.",
            "character_arc_summary": "A summary of how this character will grow and change throughout the story."
        }
    
    def _update_character(self, story_id: str, character: Dict[str, Any]):
        query = """
        MATCH (c:Character {story_id: $story_id, name: $name})
        SET c.backstory = $backstory,
            c.motivation = $motivation,
            c.fears = $fears,
            c.personality_traits = $personality_traits,
            c.physical_description = $physical_description,
            c.character_arc_summary = $character_arc_summary
        """
        self.neo4j_tool.query(query, {
            "story_id": story_id,
            "name": character["name"],
            "backstory": character["backstory"],
            "motivation": character["motivation"],
            "fears": character["fears"],
            "personality_traits": character["personality_traits"],
            "physical_description": character["physical_description"],
            "character_arc_summary": character["character_arc_summary"]
        })
    
    def _format_themes(self, themes: List[Dict]) -> str:
        return "\n".join([f"- {t['name']}: {t['description']}" for t in themes])
    
    def _format_character_details(self, characters: List[Dict[str, Any]]) -> str:
        details = []
        for char in characters:
            details.append(f"**{char['name']}**")
            details.append(f"Backstory: {char['backstory'][:100]}...")
            details.append(f"Motivation: {char['motivation']}")
            details.append("")
        return "\n".join(details)