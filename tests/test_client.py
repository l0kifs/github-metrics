"""Tests for GitHub GraphQL client."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from github_metrics.client import GitHubGraphQLClient
from github_metrics.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        github_token=SecretStr("test_token"),
        github_api_url="https://api.github.com/graphql",
    )


@pytest.fixture
def client(settings: Settings) -> GitHubGraphQLClient:
    """Create test client."""
    return GitHubGraphQLClient(settings)


def test_client_initialization(client: GitHubGraphQLClient, settings: Settings) -> None:
    """Test client initialization."""
    assert client.api_url == settings.github_api_url
    expected_auth = f"Bearer {settings.github_token.get_secret_value()}"
    assert client.headers["Authorization"] == expected_auth
    assert client.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_execute_query_success(client: GitHubGraphQLClient) -> None:
    """Test successful query execution."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"x-ratelimit-remaining": "4999"}
    mock_response.json.return_value = {"data": {"repository": {"name": "test-repo"}}}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "post", return_value=mock_response) as mock_post:
        query = "query { repository { name } }"
        result = await client.execute_query(query)

        assert result == {"repository": {"name": "test-repo"}}
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_execute_query_with_variables(client: GitHubGraphQLClient) -> None:
    """Test query execution with variables."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"x-ratelimit-remaining": "4999"}
    mock_response.json.return_value = {"data": {"test": "result"}}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "post", return_value=mock_response) as mock_post:
        query = "query($var: String!) { test(var: $var) }"
        variables = {"var": "value"}
        result = await client.execute_query(query, variables)

        assert result == {"test": "result"}
        call_args = mock_post.call_args
        assert call_args[1]["json"]["variables"] == variables


@pytest.mark.asyncio
async def test_execute_query_with_errors(client: GitHubGraphQLClient) -> None:
    """Test query execution with GraphQL errors."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"x-ratelimit-remaining": "4999"}
    mock_response.json.return_value = {
        "errors": [{"message": "Test error"}],
        "data": None,
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "post", return_value=mock_response):
        query = "query { invalid }"

        with pytest.raises(ValueError, match="GraphQL errors"):
            await client.execute_query(query)


@pytest.mark.asyncio
async def test_execute_query_primary_rate_limit(client: GitHubGraphQLClient) -> None:
    """Test query execution with primary rate limit handling."""
    import time

    # First response: rate limited
    rate_limited_response = MagicMock()
    rate_limited_response.status_code = 200
    rate_limited_response.headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": str(int(time.time()) + 1),  # Reset in 1 second
    }
    rate_limited_response.json.return_value = {"data": {"test": "rate_limited"}}
    rate_limited_response.raise_for_status = MagicMock()

    # Second response: success
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.headers = {
        "x-ratelimit-remaining": "4999",
        "x-ratelimit-reset": str(int(time.time()) + 3600),
    }
    success_response.json.return_value = {"data": {"test": "success"}}
    success_response.raise_for_status = MagicMock()

    with (
        patch.object(
            client.client, "post", side_effect=[rate_limited_response, success_response]
        ) as mock_post,
        patch("asyncio.sleep") as mock_sleep,
    ):
        query = "query { test }"
        result = await client.execute_query(query)

        assert result == {"test": "success"}
        assert mock_post.call_count == 2
        assert mock_sleep.call_count >= 1  # At least one sleep for rate limit


@pytest.mark.asyncio
async def test_execute_query_secondary_rate_limit(client: GitHubGraphQLClient) -> None:
    """Test query execution with secondary rate limit handling."""
    # First response: rate limited with retry-after
    rate_limited_response = MagicMock()
    rate_limited_response.status_code = 403
    rate_limited_response.headers = {"retry-after": "30"}
    rate_limited_response.json.return_value = {"message": "API rate limit exceeded"}
    rate_limited_response.raise_for_status = MagicMock(side_effect=Exception("403"))

    # Second response: success
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.headers = {}
    success_response.json.return_value = {"data": {"test": "success"}}
    success_response.raise_for_status = MagicMock()

    with (
        patch.object(
            client.client, "post", side_effect=[rate_limited_response, success_response]
        ) as mock_post,
        patch("asyncio.sleep") as mock_sleep,
    ):
        query = "query { test }"
        result = await client.execute_query(query)

        assert result == {"test": "success"}
        assert mock_post.call_count == 2
        mock_sleep.assert_called_with(30)


@pytest.mark.asyncio
async def test_execute_query_max_retries_exceeded(client: GitHubGraphQLClient) -> None:
    """Test query execution when max retries are exceeded."""
    from httpx import HTTPStatusError

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock(
        side_effect=HTTPStatusError("500", request=MagicMock(), response=mock_response)
    )
    mock_response.json = MagicMock()  # Not called since raise_for_status fails

    with (
        patch.object(client.client, "post", return_value=mock_response) as mock_post,
        patch("asyncio.sleep") as mock_sleep,
    ):
        query = "query { test }"

        with pytest.raises(HTTPStatusError):
            await client.execute_query(query)

        # Should attempt 5 times (max_retries)
        assert mock_post.call_count == 5
        assert mock_sleep.call_count == 4  # 4 retries


@pytest.mark.asyncio
async def test_get_pr_diff_success(client: GitHubGraphQLClient) -> None:
    """Test successful PR diff fetching."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"x-ratelimit-remaining": "4999"}
    mock_response.text = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def test():
     pass
+    return True
"""
    mock_response.raise_for_status = MagicMock()

    with patch.object(client.client, "get", return_value=mock_response) as mock_get:
        diff = await client.get_pr_diff("owner", "repo", 123)

        assert "diff --git" in diff
        assert "+    return True" in diff
        mock_get.assert_called_once()
        # Verify correct URL was called
        call_args = mock_get.call_args
        assert "/repos/owner/repo/pulls/123" in call_args[0][0]
        # Verify diff accept header
        assert call_args[1]["headers"]["Accept"] == "application/vnd.github.diff"
