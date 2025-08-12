import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from agent.state import AgentState
from agent.tools.knowledge_graph import Neo4jTool

logger = logging.getLogger(__name__)


class ArchitectAgent:
    def __init__(self, llm: ChatOpenAI, neo4j_tool: Neo4jTool):
        self.llm = llm
        self.neo4j_tool = neo4j_tool
        
        self.arc_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are the Architect Agent, responsible for building story structure hierarchically.
            
Your task is to create story arcs based on the established themes and characters.
Create 2-4 compelling arcs that:
1. Each serve the overall story themes
2. Provide character development opportunities  
3. Build toward a satisfying climax
4. Have clear beginning, middle, and end

Format your response as a structured list of arcs with titles and summaries."""),
            ("user", "Story Context:\nThemes: {themes}\nCharacters: {characters}\nPrompt: {prompt}\n\nCreate the story arcs.")
        ])
        
        self.chapter_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are creating chapters for a story arc.
            
Break down the arc into 3-6 chapters that:
1. Have clear narrative beats
2. Advance character arcs
3. Build tension appropriately
4. Include dramatic moments

Format as numbered chapters with summaries."""),
            ("user", "Arc: {arc_title}\nSummary: {arc_summary}\nStory Context: {context}\n\nCreate chapters for this arc.")
        ])
        
        self.scene_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are creating scenes for a chapter.
            
Break down the chapter into 2-4 scenes that:
1. Each focus on a specific dramatic beat
2. Have clear objectives for characters
3. Advance the plot meaningfully
4. Set up the next scene naturally

Format as scene descriptions with beat sheets."""),
            ("user", "Chapter {chapter_num}: {chapter_summary}\nArc Context: {arc_context}\n\nCreate scenes for this chapter.")
        ])
    
    def run(self, state: AgentState) -> Dict[str, Any]:
        try:
            story_id = state["story_id"]
            task_queue = state.get("task_queue", [])
            
            if not task_queue:
                return {"system_status": "ERROR", "messages": state["messages"] + [{"type": "error", "content": "No architect tasks in queue"}]}
            
            current_task = task_queue[0]
            task_type = current_task.get("task")
            
            if task_type == "generate_arcs":
                return self._generate_arcs(state)
            elif task_type == "generate_chapters":
                return self._generate_chapters(state, current_task.get("arc_title"))
            elif task_type == "generate_scenes":
                return self._generate_scenes(state, current_task.get("chapter_number"))
            else:
                return {"system_status": "ERROR", "messages": state["messages"] + [{"type": "error", "content": f"Unknown architect task: {task_type}"}]}
                
        except Exception as e:
            logger.error(f"Architect error: {e}")
            return {
                "system_status": "ERROR",
                "messages": state["messages"] + [{
                    "type": "error",
                    "content": f"Architect failed: {str(e)}",
                    "timestamp": None
                }]
            }
    
    def _generate_arcs(self, state: AgentState) -> Dict[str, Any]:
        story_id = state["story_id"]
        logger.info(f"Architect generating arcs for story {story_id}")
        
        # Get story context
        context = self._get_story_context(story_id)
        
        # Generate arcs
        response = self.llm.invoke(self.arc_prompt.format_messages(
            themes=self._format_themes(context["themes"]),
            characters=self._format_characters(context["characters"]),
            prompt=context["prompt"]
        ))
        
        arcs_text = response.content
        arcs = self._parse_arcs(arcs_text)
        
        # Add arcs to knowledge graph
        for arc in arcs:
            self.neo4j_tool.add_arc(story_id, arc["title"], arc["summary"])
        
        # Update task queue for next phase
        new_tasks = [{"task": "generate_chapters", "arc_title": arc["title"]} for arc in arcs]
        
        return {
            "system_status": "AWAITING_USER_APPROVAL_FOR_ARCS",
            "task_queue": state["task_queue"][1:] + new_tasks,  # Remove current task, add new ones
            "messages": state["messages"] + [{
                "type": "agent_step",
                "agent": "Architect", 
                "content": f"Generated {len(arcs)} story arcs",
                "details": arcs_text,
                "timestamp": None
            }]
        }
    
    def _generate_chapters(self, state: AgentState, arc_title: str) -> Dict[str, Any]:
        story_id = state["story_id"]
        logger.info(f"Architect generating chapters for arc: {arc_title}")
        
        # Get arc details
        arc_query = """
        MATCH (a:Arc {story_id: $story_id, arc_title: $arc_title})
        RETURN a.summary as summary
        """
        arc_result = self.neo4j_tool.query(arc_query, {"story_id": story_id, "arc_title": arc_title})
        
        if not arc_result:
            return {"system_status": "ERROR", "messages": state["messages"] + [{"type": "error", "content": f"Arc {arc_title} not found"}]}
        
        arc_summary = arc_result[0]["summary"]
        context = self._get_story_context(story_id)
        
        # Generate chapters
        response = self.llm.invoke(self.chapter_prompt.format_messages(
            arc_title=arc_title,
            arc_summary=arc_summary,
            context=str(context)
        ))
        
        chapters_text = response.content
        chapters = self._parse_chapters(chapters_text)
        
        # Add chapters to knowledge graph
        for i, chapter in enumerate(chapters, 1):
            self.neo4j_tool.add_chapter(story_id, arc_title, i, chapter["summary"])
        
        # Update task queue
        new_tasks = [{"task": "generate_scenes", "chapter_number": i} for i in range(1, len(chapters) + 1)]
        remaining_tasks = [task for task in state["task_queue"][1:] if task.get("arc_title") != arc_title]
        
        return {
            "system_status": "AWAITING_USER_APPROVAL_FOR_CHAPTERS",
            "task_queue": remaining_tasks + new_tasks,
            "messages": state["messages"] + [{
                "type": "agent_step", 
                "agent": "Architect",
                "content": f"Generated {len(chapters)} chapters for arc '{arc_title}'",
                "details": chapters_text,
                "timestamp": None
            }]
        }
    
    def _generate_scenes(self, state: AgentState, chapter_number: int) -> Dict[str, Any]:
        story_id = state["story_id"]
        logger.info(f"Architect generating scenes for chapter {chapter_number}")
        
        # Get chapter details
        chapter_query = """
        MATCH (c:Chapter {story_id: $story_id, chapter_number: $chapter_number})
        MATCH (c)-[:PART_OF]->(a:Arc)
        RETURN c.summary as summary, a.arc_title as arc_title, a.summary as arc_summary
        """
        chapter_result = self.neo4j_tool.query(chapter_query, {"story_id": story_id, "chapter_number": chapter_number})
        
        if not chapter_result:
            return {"system_status": "ERROR", "messages": state["messages"] + [{"type": "error", "content": f"Chapter {chapter_number} not found"}]}
        
        chapter_data = chapter_result[0]
        
        # Generate scenes
        response = self.llm.invoke(self.scene_prompt.format_messages(
            chapter_num=chapter_number,
            chapter_summary=chapter_data["summary"],
            arc_context=f"Arc: {chapter_data['arc_title']} - {chapter_data['arc_summary']}"
        ))
        
        scenes_text = response.content
        scenes = self._parse_scenes(scenes_text, chapter_number)
        
        # Add scenes to knowledge graph
        for scene in scenes:
            self.neo4j_tool.add_scene(story_id, chapter_number, scene["scene_id"], scene["beat_sheet"])
        
        # Remove current task from queue
        return {
            "system_status": "READY_FOR_WRITING" if not [t for t in state["task_queue"][1:] if t.get("task") == "generate_scenes"] else "AWAITING_USER_APPROVAL_FOR_SCENES",
            "task_queue": state["task_queue"][1:],
            "messages": state["messages"] + [{
                "type": "agent_step",
                "agent": "Architect", 
                "content": f"Generated {len(scenes)} scenes for chapter {chapter_number}",
                "details": scenes_text,
                "timestamp": None
            }]
        }
    
    def _get_story_context(self, story_id: str) -> Dict[str, Any]:
        # Get themes
        themes_query = """
        MATCH (t:Theme {story_id: $story_id})
        RETURN collect({name: t.name, description: t.description}) as themes
        """
        themes_result = self.neo4j_tool.query(themes_query, {"story_id": story_id})
        
        # Get characters
        characters_query = """
        MATCH (c:Character {story_id: $story_id})
        RETURN collect({name: c.name, backstory: c.backstory, motivation: c.motivation}) as characters
        """
        characters_result = self.neo4j_tool.query(characters_query, {"story_id": story_id})
        
        # Get story prompt
        story_query = """
        MATCH (s:Story {story_id: $story_id})
        RETURN s.prompt as prompt
        """
        story_result = self.neo4j_tool.query(story_query, {"story_id": story_id})
        
        return {
            "themes": themes_result[0]["themes"] if themes_result else [],
            "characters": characters_result[0]["characters"] if characters_result else [],
            "prompt": story_result[0]["prompt"] if story_result else ""
        }
    
    def _format_themes(self, themes: List[Dict]) -> str:
        return "\n".join([f"- {t['name']}: {t['description']}" for t in themes])
    
    def _format_characters(self, characters: List[Dict]) -> str:
        return "\n".join([f"- {c['name']}: {c.get('backstory', 'TBD')}" for c in characters])
    
    def _parse_arcs(self, text: str) -> List[Dict[str, str]]:
        # Simplified parsing - in practice would use structured output
        return [
            {"title": "Act 1: Discovery", "summary": "The protagonist discovers their true nature and the world they're entering"},
            {"title": "Act 2: Trials", "summary": "Facing challenges and growing stronger while uncovering deeper mysteries"},
            {"title": "Act 3: Resolution", "summary": "Final confrontation and resolution of all plot threads"}
        ]
    
    def _parse_chapters(self, text: str) -> List[Dict[str, str]]:
        # Simplified parsing
        return [
            {"summary": "Introduction of protagonist and initial conflict"},
            {"summary": "First major challenge and character growth"},
            {"summary": "Climax and resolution of the arc"}
        ]
    
    def _parse_scenes(self, text: str, chapter_number: int) -> List[Dict[str, str]]:
        # Simplified parsing
        return [
            {"scene_id": f"{chapter_number}.1", "beat_sheet": "Opening scene establishing mood and conflict"},
            {"scene_id": f"{chapter_number}.2", "beat_sheet": "Development and escalation of tension"},
            {"scene_id": f"{chapter_number}.3", "beat_sheet": "Resolution and transition to next chapter"}
        ]