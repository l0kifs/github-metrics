"""Tests for GitHub GraphQL client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_metrics.client import GitHubGraphQLClient
from github_metrics.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        github_token="test_token",
        github_api_url="https://api.github.com/graphql",
    )


@pytest.fixture
def client(settings: Settings) -> GitHubGraphQLClient:
    """Create test client."""
    return GitHubGraphQLClient(settings)


def test_client_initialization(client: GitHubGraphQLClient, settings: Settings) -> None:
    """Test client initialization."""
    assert client.api_url == settings.github_api_url
    assert client.headers["Authorization"] == f"Bearer {settings.github_token}"
    assert client.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_execute_query_success(client: GitHubGraphQLClient) -> None:
    """Test successful query execution."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"repository": {"name": "test-repo"}}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        query = "query { repository { name } }"
        result = await client.execute_query(query)

        assert result == {"repository": {"name": "test-repo"}}
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_execute_query_with_variables(client: GitHubGraphQLClient) -> None:
    """Test query execution with variables."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"test": "result"}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        query = "query($var: String!) { test(var: $var) }"
        variables = {"var": "value"}
        result = await client.execute_query(query, variables)

        assert result == {"test": "result"}
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["variables"] == variables


@pytest.mark.asyncio
async def test_execute_query_with_errors(client: GitHubGraphQLClient) -> None:
    """Test query execution with GraphQL errors."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "errors": [{"message": "Test error"}],
        "data": None,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        query = "query { invalid }"

        with pytest.raises(ValueError, match="GraphQL errors"):
            await client.execute_query(query)
