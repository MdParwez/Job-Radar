from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    tavily_api_key: str = ""
    frontend_origin: str = "http://localhost:5173"
    job_max_age_hours: int = 24

    # Adzuna (free tier, official API) - covers UK/Germany/Poland/Australia/Brazil.
    # Optional: leave blank and that source just returns no results.
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # Langfuse (free, self-hostable or cloud.langfuse.com) - tool-call/latency/token monitoring
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"


settings = Settings()
