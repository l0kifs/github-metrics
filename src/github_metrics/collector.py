"""GitHub metrics collector service."""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from github_metrics.client import GitHubGraphQLClient
from github_metrics.config.logging import setup_logging
from github_metrics.config.settings import Settings
from github_metrics.models import PRMetrics, PRResolution, RepositoryMetrics, User
from github_metrics.queries import PULL_REQUESTS_QUERY


class MetricsCollector:
    """Collector for GitHub PR metrics."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize metrics collector.

        Args:
            settings: Application settings
        """
        setup_logging()
        self.client = GitHubGraphQLClient(settings)

    async def collect_pr_metrics(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime,
        base_branch: str | None = None,
        timeout: float | None = None,
    ) -> RepositoryMetrics:
        """
        Collect PR metrics for a repository within a time period.

        Args:
            owner: Repository owner
            repo: Repository name
            start_date: Start of the period (inclusive)
            end_date: End of the period (inclusive)
            base_branch: Optional target branch filter (e.g., 'main', 'develop')
            timeout: Optional timeout for API requests in seconds

        Returns:
            Repository metrics containing all PRs closed in the period
        """
        logger.info(
            "Starting PR metrics collection",
            owner=owner,
            repo=repo,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            base_branch=base_branch,
        )

        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=UTC)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=UTC)

        pull_requests: list[PRMetrics] = []
        has_next_page = True
        cursor = None

        while has_next_page:
            logger.debug("Fetching page of pull requests", cursor=cursor)

            variables = {
                "owner": owner,
                "repo": repo,
                "states": ["CLOSED", "MERGED"],
                "after": cursor,
                "first": self.client.settings.github_page_size,
            }

            data = await self.client.execute_query(
                PULL_REQUESTS_QUERY, variables, timeout
            )

            repository_data = data.get("repository", {})
            pr_data = repository_data.get("pullRequests", {})
            page_info = pr_data.get("pageInfo", {})
            pr_nodes = pr_data.get("nodes", [])

            for pr_node in pr_nodes:
                # Skip draft PRs
                if pr_node.get("isDraft", False):
                    logger.debug("Skipping draft PR", pr_number=pr_node.get("number"))
                    continue

                # Parse updated_at for pagination
                updated_at_str = pr_node.get("updatedAt")
                if not updated_at_str:
                    continue
                updated_at = datetime.fromisoformat(
                    updated_at_str.replace("Z", "+00:00")
                )

                # If PR was last updated before start_date, since we're sorting
                # by UPDATED_AT DESC, we can stop pagination
                if updated_at < start_date:
                    logger.debug(
                        "PR last updated before start date, stopping pagination",
                        pr_number=pr_node.get("number"),
                        updated_at=updated_at.isoformat(),
                    )
                    has_next_page = False
                    break

                # Parse PR metrics (we'll filter by closed_at later)
                try:
                    pr_metrics = self._parse_pr_metrics(pr_node)
                    pull_requests.append(pr_metrics)
                    logger.debug(
                        "Collected PR metrics",
                        pr_number=pr_metrics.number,
                        resolution=pr_metrics.resolution,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to parse PR metrics, skipping PR",
                        pr_number=pr_node.get("number"),
                        error=str(e),
                        exc_info=True,
                    )
                    continue

            # Check for next page
            if page_info.get("hasNextPage", False):
                cursor = page_info.get("endCursor")
            else:
                has_next_page = False

        # Filter collected PRs by closed_at date range and optionally by base branch
        filtered_pull_requests = [
            pr
            for pr in pull_requests
            if start_date <= pr.closed_at <= end_date
            and (base_branch is None or pr.base_branch == base_branch)
        ]

        logger.info(
            "Completed PR metrics collection",
            total_collected=len(pull_requests),
            total_filtered=len(filtered_pull_requests),
            owner=owner,
            repo=repo,
        )

        return RepositoryMetrics(
            repository=f"{owner}/{repo}",
            period_start=start_date,
            period_end=end_date,
            pull_requests=filtered_pull_requests,
        )

    async def close(self) -> None:
        """Close the client."""
        await self.client.close()

    def _parse_pr_metrics(self, pr_node: dict[str, Any]) -> PRMetrics:
        """
        Parse PR node from GraphQL response into PRMetrics model.

        Args:
            pr_node: PR node from GraphQL response

        Returns:
            Parsed PR metrics
        """
        # Basic info
        number = pr_node.get("number", 0)
        title = pr_node.get("title", "")
        url = pr_node.get("url", "")
        base_branch = pr_node.get("baseRefName", "unknown")

        # Author
        author_data = pr_node.get("author") or {}
        author = User(
            login=author_data.get("login", "unknown"),
            name=author_data.get("name"),
        )

        # Dates
        created_at_str = pr_node.get("createdAt", "")
        closed_at_str = pr_node.get("closedAt", "")

        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        closed_at = datetime.fromisoformat(closed_at_str.replace("Z", "+00:00"))
        merged_at_str = pr_node.get("mergedAt")
        merged_at = (
            datetime.fromisoformat(merged_at_str.replace("Z", "+00:00"))
            if merged_at_str
            else None
        )

        # Resolution
        resolution = (
            PRResolution.MERGED if merged_at else PRResolution.CLOSED_NOT_MERGED
        )

        # Changes
        additions = pr_node.get("additions", 0)
        deletions = pr_node.get("deletions", 0)
        changes_count = additions + deletions

        # Review time (from creation to closure, accounting for reopenings)
        timeline_items = pr_node.get("timelineItems", {}).get("nodes", [])

        # Sort timeline events by createdAt
        events = []
        for item in timeline_items:
            event_type = item.get("__typename")
            if event_type in ["ClosedEvent", "ReopenedEvent"]:
                events.append(
                    {
                        "type": event_type,
                        "timestamp": datetime.fromisoformat(
                            item.get("createdAt", "").replace("Z", "+00:00")
                        ),
                    }
                )

        events.sort(key=lambda x: x["timestamp"])

        # Calculate review time: sum of periods when PR was open
        review_time_hours = 0.0
        current_open_start: datetime | None = created_at

        for event in events:
            if event["type"] == "ClosedEvent":
                # PR was closed, add time from open start to this close
                review_time_hours += (
                    event["timestamp"] - current_open_start
                ).total_seconds() / 3600
                current_open_start = None  # PR is now closed
            elif event["type"] == "ReopenedEvent" and current_open_start is None:
                # PR was reopened, start new open period
                current_open_start = event["timestamp"]

        # If PR ended open (but it shouldn't since we're looking at closed PRs),
        # add remaining time
        if current_open_start is not None:
            review_time_hours += (closed_at - current_open_start).total_seconds() / 3600

        # Commits
        commits_count = pr_node.get("commits", {}).get("totalCount", 0)

        # Comments
        comments_count = pr_node.get("comments", {}).get("totalCount", 0)

        # Review comments
        review_threads = pr_node.get("reviewThreads", {})
        review_comments_count = sum(
            thread.get("comments", {}).get("totalCount", 0)
            for thread in review_threads.get("nodes", [])
        )

        # Reviews and approvers
        reviews = pr_node.get("reviews", {}).get("nodes", [])
        approvers_set = set()
        commenters_set = set()

        for review in reviews:
            review_author = review.get("author")
            if review_author:
                login = review_author.get("login")
                name = review_author.get("name")
                if login:
                    if review.get("state") == "APPROVED":
                        approvers_set.add((login, name))
                    else:
                        commenters_set.add((login, name))

        approvers = [User(login=login, name=name) for login, name in approvers_set]
        commenters = [User(login=login, name=name) for login, name in commenters_set]

        # Labels
        labels_data = pr_node.get("labels", {}).get("nodes", [])
        labels = [label["name"] for label in labels_data if "name" in label]

        # Description
        description = pr_node.get("body", "")

        return PRMetrics(
            number=number,
            title=title,
            url=url,
            base_branch=base_branch,
            author=author,
            created_at=created_at,
            closed_at=closed_at,
            merged_at=merged_at,
            resolution=resolution,
            changes_count=changes_count,
            review_time_hours=review_time_hours,
            commits_count=commits_count,
            review_comments_count=review_comments_count,
            comments_count=comments_count,
            approvers=approvers,
            commenters=commenters,
            labels=labels,
            description=description,
        )
