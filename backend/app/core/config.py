from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    
    # Neo4j Configuration
    neo4j_uri: str
    neo4j_user: str = "neo4j"
    neo4j_password: str
    
    # Redis/Celery Configuration
    celery_broker_url: str
    celery_result_backend: str
    
    # LLM Configuration
    openai_api_key: str
    
    # Application Settings
    debug: bool = False
    api_prefix: str = "/api"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()