from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    jwt_secret: str = "change-me"
    access_token_minutes: int = 60
    storage_path: str = "./storage"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
