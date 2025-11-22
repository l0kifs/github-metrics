"""GitHub GraphQL API client."""

from typing import Any

import httpx
from loguru import logger

from github_metrics.config.settings import Settings


class GitHubGraphQLClient:
    """Async client for GitHub GraphQL API."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize GitHub GraphQL client.

        Args:
            settings: Application settings containing GitHub token and API URL
        """
        self.settings = settings
        self.api_url = settings.github_api_url
        self.headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Content-Type": "application/json",
        }

    async def execute_query(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against GitHub API.

        Args:
            query: GraphQL query string
            variables: Optional variables for the query

        Returns:
            Response data from the API

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables

            logger.debug(
                "Executing GraphQL query",
                query_length=len(query),
                has_variables=variables is not None,
            )

            response = await client.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=self.settings.github_api_timeout,
            )
            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                logger.error("GraphQL query returned errors", errors=data["errors"])
                raise ValueError(f"GraphQL errors: {data['errors']}")

            logger.debug("GraphQL query executed successfully")
            return data.get("data", {})
