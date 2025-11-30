"""GitHub GraphQL API client."""

import asyncio
import time
from typing import Any, Self

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
            "Authorization": f"Bearer {settings.github_token.get_secret_value()}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=self.settings.github_api_timeout,
        )

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager and close the client."""
        await self.close()

    async def execute_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against GitHub API.

        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            timeout: Optional timeout for this request in seconds

        Returns:
            Response data from the API

        Raises:
            httpx.HTTPStatusError: If the API request fails after retries
            ValueError: If GraphQL errors are present in the response
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        logger.debug(
            "Executing GraphQL query",
            query_length=len(query),
            has_variables=variables is not None,
        )

        max_retries = 5
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            response = await self.client.post(
                self.api_url,
                json=payload,
                timeout=timeout
                if timeout is not None
                else self.settings.github_api_timeout,
            )

            # Check for rate limiting before processing response
            rate_limited = await self._handle_rate_limits(response)
            if rate_limited:
                # If rate limited, sleep and retry
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Query failed after all retries",
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=str(e),
                    )
                    raise

                delay = base_delay * (2**attempt)  # Exponential backoff
                logger.warning(
                    "Query attempt failed, retrying",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
                continue

            data = response.json()

            if "errors" in data:
                error_messages = [
                    error.get("message", "Unknown error") for error in data["errors"]
                ]
                error_summary = "; ".join(error_messages)
                logger.error("GraphQL query returned errors", errors=error_summary)
                raise ValueError(f"GraphQL errors: {error_summary}")

            result: dict[str, Any] = data.get("data", {})
            logger.debug(
                "GraphQL query executed successfully", response_keys=list(result.keys())
            )
            return result

        # If we get here, all retries failed
        raise RuntimeError(f"Query failed after {max_retries} attempts")

    async def _handle_rate_limits(self, response: httpx.Response) -> bool:
        """
        Handle GitHub API rate limits based on response headers.

        Args:
            response: HTTP response from GitHub API

        Returns:
            True if rate limited and should retry, False otherwise
        """
        # Check primary rate limit headers
        remaining = response.headers.get("x-ratelimit-remaining")
        reset_time = response.headers.get("x-ratelimit-reset")
        retry_after = response.headers.get("retry-after")

        if remaining is not None:
            remaining = int(remaining)
            logger.debug(
                "Rate limit status",
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
            )

            if remaining == 0 and reset_time:
                # Primary rate limit exceeded
                reset_timestamp = int(reset_time)
                current_time = int(time.time())
                wait_time = max(0, reset_timestamp - current_time)

                logger.warning(
                    "Primary rate limit exceeded, waiting until reset",
                    wait_time=wait_time,
                    reset_timestamp=reset_timestamp,
                )
                await asyncio.sleep(wait_time)
                return True

        if retry_after:
            # Secondary rate limit exceeded
            wait_time = int(retry_after)
            logger.warning(
                "Secondary rate limit exceeded, waiting",
                retry_after=wait_time,
            )
            await asyncio.sleep(wait_time)
            return True

        # Check for rate limit error messages in response body
        if response.status_code in (403, 200):  # 200 can contain rate limit errors
            try:
                data = response.json()
                if "errors" in data:
                    for error in data["errors"]:
                        message = error.get("message", "").lower()
                        if "rate limit" in message or "abuse" in message:
                            logger.warning(
                                "Rate limit detected in error message",
                                error_message=message,
                            )
                            # Wait for a default backoff time
                            await asyncio.sleep(60)  # 1 minute
                            return True
            except Exception:
                pass  # Ignore JSON parsing errors

        return False

    async def get_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        timeout: float | None = None,
    ) -> str:
        """
        Fetch the diff for a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            timeout: Optional timeout for this request in seconds

        Returns:
            The PR diff as a string in unified diff format

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        # Use REST API endpoint for PR diff
        # Replace graphql URL with REST API base
        base_url = self.api_url.replace("/graphql", "")
        url = f"{base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

        headers = {
            **self.headers,
            "Accept": "application/vnd.github.diff",
        }

        logger.debug(
            "Fetching PR diff",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
        )

        response = await self.client.get(
            url,
            headers=headers,
            timeout=timeout
            if timeout is not None
            else self.settings.github_api_timeout,
        )

        # Handle rate limits
        rate_limited = await self._handle_rate_limits(response)
        if rate_limited:
            # Retry once after rate limit
            response = await self.client.get(
                url,
                headers=headers,
                timeout=timeout
                if timeout is not None
                else self.settings.github_api_timeout,
            )

        response.raise_for_status()

        logger.debug(
            "PR diff fetched successfully",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            diff_length=len(response.text),
        )

        return response.text

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
