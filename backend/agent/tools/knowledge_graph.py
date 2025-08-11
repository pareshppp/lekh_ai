import os
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class Neo4jTool:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        
        self.driver = GraphDatabase.driver(
            self.uri, 
            auth=(self.user, self.password)
        )
    
    def close(self):
        self.driver.close()
    
    def query(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        with self.driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            return [record.data() for record in result]
    
    def create_story_node(self, story_id: str, title: str, prompt: str, genres: List[str]) -> str:
        query = """
        CREATE (s:Story {
            story_id: $story_id,
            title: $title,
            prompt: $prompt,
            genres: $genres,
            created_at: datetime()
        })
        RETURN s.story_id as story_id
        """
        result = self.query(query, {
            "story_id": story_id,
            "title": title,
            "prompt": prompt,
            "genres": genres
        })
        return result[0]["story_id"]
    
    def add_theme(self, story_id: str, name: str, description: str) -> str:
        query = """
        MATCH (s:Story {story_id: $story_id})
        CREATE (t:Theme {
            story_id: $story_id,
            name: $name,
            description: $description
        })
        CREATE (s)-[:HAS_THEME]->(t)
        RETURN t.name as theme_name
        """
        result = self.query(query, {
            "story_id": story_id,
            "name": name,
            "description": description
        })
        return result[0]["theme_name"]
    
    def add_character(self, story_id: str, name: str, details: Dict[str, Any]) -> str:
        query = """
        MATCH (s:Story {story_id: $story_id})
        CREATE (c:Character {
            story_id: $story_id,
            name: $name,
            backstory: $backstory,
            motivation: $motivation,
            fears: $fears,
            personality_traits: $personality_traits,
            physical_description: $physical_description,
            character_arc_summary: $character_arc_summary
        })
        CREATE (s)-[:CONTAINS]->(c)
        RETURN c.name as character_name
        """
        result = self.query(query, {
            "story_id": story_id,
            "name": name,
            **details
        })
        return result[0]["character_name"]
    
    def add_location(self, story_id: str, name: str, description: str, atmosphere: str, historical_significance: str = None) -> str:
        query = """
        MATCH (s:Story {story_id: $story_id})
        CREATE (l:Location {
            story_id: $story_id,
            name: $name,
            description: $description,
            atmosphere: $atmosphere,
            historical_significance: $historical_significance
        })
        CREATE (s)-[:CONTAINS]->(l)
        RETURN l.name as location_name
        """
        result = self.query(query, {
            "story_id": story_id,
            "name": name,
            "description": description,
            "atmosphere": atmosphere,
            "historical_significance": historical_significance
        })
        return result[0]["location_name"]
    
    def add_arc(self, story_id: str, arc_title: str, summary: str) -> str:
        query = """
        MATCH (s:Story {story_id: $story_id})
        CREATE (a:Arc {
            story_id: $story_id,
            arc_title: $arc_title,
            summary: $summary
        })
        CREATE (s)-[:CONTAINS]->(a)
        RETURN a.arc_title as arc_title
        """
        result = self.query(query, {
            "story_id": story_id,
            "arc_title": arc_title,
            "summary": summary
        })
        return result[0]["arc_title"]
    
    def add_chapter(self, story_id: str, arc_title: str, chapter_number: int, summary: str) -> int:
        query = """
        MATCH (a:Arc {story_id: $story_id, arc_title: $arc_title})
        CREATE (c:Chapter {
            story_id: $story_id,
            chapter_number: $chapter_number,
            summary: $summary
        })
        CREATE (c)-[:PART_OF]->(a)
        RETURN c.chapter_number as chapter_number
        """
        result = self.query(query, {
            "story_id": story_id,
            "arc_title": arc_title,
            "chapter_number": chapter_number,
            "summary": summary
        })
        return result[0]["chapter_number"]
    
    def add_scene(self, story_id: str, chapter_number: int, scene_id: str, beat_sheet: str, status: str = "outlined") -> str:
        query = """
        MATCH (ch:Chapter {story_id: $story_id, chapter_number: $chapter_number})
        CREATE (s:Scene {
            story_id: $story_id,
            scene_id: $scene_id,
            beat_sheet: $beat_sheet,
            prose_content: "",
            status: $status
        })
        CREATE (s)-[:PART_OF]->(ch)
        RETURN s.scene_id as scene_id
        """
        result = self.query(query, {
            "story_id": story_id,
            "chapter_number": chapter_number,
            "scene_id": scene_id,
            "beat_sheet": beat_sheet,
            "status": status
        })
        return result[0]["scene_id"]
    
    def get_scene_context(self, story_id: str, scene_id: str) -> Dict[str, Any]:
        query = """
        MATCH (scene:Scene {story_id: $story_id, scene_id: $scene_id})
        MATCH (scene)-[:PART_OF]->(chapter:Chapter)-[:PART_OF]->(arc:Arc)
        OPTIONAL MATCH (scene)-[:APPEARS_IN]<-(character:Character)
        OPTIONAL MATCH (scene)-[:LOCATED_IN]->(location:Location)
        OPTIONAL MATCH (prev:Scene)-[:PRECEDES]->(scene)
        RETURN scene, chapter, arc, 
               collect(DISTINCT character) as characters,
               location,
               collect(DISTINCT prev.scene_id) as previous_scenes
        """
        result = self.query(query, {"story_id": story_id, "scene_id": scene_id})
        if result:
            return result[0]
        return {}
    
    def update_scene_prose(self, story_id: str, scene_id: str, prose_content: str, status: str = "written") -> bool:
        query = """
        MATCH (s:Scene {story_id: $story_id, scene_id: $scene_id})
        SET s.prose_content = $prose_content, s.status = $status
        RETURN s.scene_id as updated_scene_id
        """
        result = self.query(query, {
            "story_id": story_id,
            "scene_id": scene_id,
            "prose_content": prose_content,
            "status": status
        })
        return len(result) > 0
    
    def get_scenes_with_status(self, story_id: str, status: str) -> List[str]:
        query = """
        MATCH (s:Scene {story_id: $story_id, status: $status})
        RETURN s.scene_id as scene_id
        ORDER BY s.scene_id
        """
        result = self.query(query, {"story_id": story_id, "status": status})
        return [record["scene_id"] for record in result]
    
    def delete_story_nodes(self, story_id: str) -> bool:
        query = """
        MATCH (n {story_id: $story_id})
        DETACH DELETE n
        """
        try:
            self.query(query, {"story_id": story_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting story nodes for {story_id}: {e}")
            return False
    
    def get_story_outline(self, story_id: str) -> Dict[str, Any]:
        query = """
        MATCH (story:Story {story_id: $story_id})
        OPTIONAL MATCH (story)-[:CONTAINS]->(arc:Arc)
        OPTIONAL MATCH (arc)<-[:PART_OF]-(chapter:Chapter)
        OPTIONAL MATCH (chapter)<-[:PART_OF]-(scene:Scene)
        RETURN story, 
               collect(DISTINCT arc) as arcs,
               collect(DISTINCT chapter) as chapters,
               collect(DISTINCT scene) as scenes
        """
        result = self.query(query, {"story_id": story_id})
        if result:
            return result[0]
        return {}
    
    def get_characters(self, story_id: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:Character {story_id: $story_id})
        RETURN c
        """
        result = self.query(query, {"story_id": story_id})
        return [record["c"] for record in result]
    
    def get_locations(self, story_id: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (l:Location {story_id: $story_id})
        RETURN l
        """
        result = self.query(query, {"story_id": story_id})
        return [record["l"] for record in result]