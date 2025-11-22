from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings"""

    model_config = SettingsConfigDict(
        env_prefix="GITHUB_METRICS__",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="github-metrics", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")

    # Logging settings
    logging_level: str = Field(default="INFO", description="Logging level")
    logging_format: str = Field(
        default=(
            "{time:YYYY-MM-DD HH:mm:ss} | {extra[app]} v{extra[version]} | "
            "{level: <8} | {name}:{function}:{line} - {message} | {extra}"
        ),
        description="Console log format",
    )

    # GitHub API settings
    github_token: str = Field(
        default="", description="GitHub Personal Access Token for API authentication"
    )
    github_api_url: str = Field(
        default="https://api.github.com/graphql",
        description="GitHub GraphQL API URL",
    )
    github_api_timeout: float = Field(
        default=120.0,
        description="GitHub API request timeout in seconds",
    )


def get_settings() -> Settings:
    """Retrieve application settings"""
    return Settings()
