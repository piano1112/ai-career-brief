"""환경변수 설정. 모든 설정은 여기서만 읽는다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (Milestone 2부터 사용). 모델명은 하드코딩하지 않고 환경변수로 받는다.
    anthropic_api_key: str = ""
    claude_model: str = ""

    database_url: str = "postgresql+psycopg://brief:brief@localhost:5432/brief"

    tz: str = "Asia/Seoul"
    briefing_publish_time: str = "07:00"

    work24_api_key: str = ""

    # 단일 계정 로그인
    admin_username: str = "me"
    admin_password_hash: str = ""
    session_secret: str = ""
    session_https_only: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
