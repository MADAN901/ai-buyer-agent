"""Application configuration from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    root = Path(__file__).resolve().parents[2]
    repo = root.parent
    candidates = (repo / ".env", root / ".env", Path(".env"))
    return tuple(str(p) for p in candidates if p.is_file()) or (str(repo / ".env"),)


def _default_database_url() -> str:
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'purchasing_agent.db').resolve()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "mock"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    model_name: str = ""

    database_url: str = _default_database_url()

    max_agent_iterations: int = 3
    max_tool_calls: int = 40
    auto_approve_limit: float = 5000.0

    mock_supplier_chaos: bool = False
    frontend_url: str = "http://localhost:5173"

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            raw = self.database_url[len(prefix) :]
            if raw.startswith("/"):
                return Path(raw)
            return Path(raw).resolve()
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
