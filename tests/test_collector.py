"""Tests for metrics collector."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from github_metrics.collector import MetricsCollector
from github_metrics.config.settings import Settings
from github_metrics.models import PRResolution


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        github_token="test_token",
        github_api_url="https://api.github.com/graphql",
    )


@pytest.fixture
def collector(settings: Settings) -> MetricsCollector:
    """Create test collector."""
    return MetricsCollector(settings)


@pytest.mark.asyncio
async def test_collect_pr_metrics_basic(collector: MetricsCollector) -> None:
    """Test basic PR metrics collection."""
    # Mock GraphQL response
    mock_data = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 1,
                        "title": "Test PR",
                        "url": "https://github.com/owner/repo/pull/1",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2024-01-10T12:00:00Z",
                        "updatedAt": "2024-01-11T12:00:00Z",
                        "closedAt": "2024-01-11T12:00:00Z",
                        "mergedAt": "2024-01-11T12:00:00Z",
                        "body": "Test description",
                        "additions": 100,
                        "deletions": 50,
                        "changedFiles": 5,
                        "commits": {"totalCount": 3},
                        "author": {"login": "testuser", "name": "Test User"},
                        "labels": {"nodes": [{"name": "bug"}]},
                        "comments": {"totalCount": 2},
                        "reviews": {
                            "nodes": [
                                {
                                    "author": {"login": "reviewer", "name": "Reviewer"},
                                    "state": "APPROVED",
                                }
                            ]
                        },
                        "reviewThreads": {"totalCount": 1, "nodes": []},
                        "timelineItems": {"nodes": []},
                    }
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, tzinfo=UTC)

        metrics = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )

        assert metrics.repository == "owner/repo"
        assert metrics.total_prs == 1
        assert metrics.merged_prs == 1
        assert metrics.closed_prs == 0

        pr = metrics.pull_requests[0]
        assert pr.number == 1
        assert pr.title == "Test PR"
        assert pr.base_branch == "main"
        assert pr.resolution == PRResolution.MERGED
        assert pr.changes_count == 150
        assert pr.commits_count == 3
        assert len(pr.approvers) == 1
        assert pr.approvers[0].login == "reviewer"


@pytest.mark.asyncio
async def test_collect_pr_metrics_skips_drafts(collector: MetricsCollector) -> None:
    """Test that draft PRs are skipped."""
    mock_data = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 1,
                        "title": "Draft PR",
                        "url": "https://github.com/owner/repo/pull/1",
                        "isDraft": True,
                        "baseRefName": "main",
                        "createdAt": "2024-01-10T12:00:00Z",
                        "updatedAt": "2024-01-11T12:00:00Z",
                        "closedAt": "2024-01-11T12:00:00Z",
                        "mergedAt": None,
                        "body": "",
                        "additions": 0,
                        "deletions": 0,
                        "changedFiles": 0,
                        "commits": {"totalCount": 0},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 1, "nodes": []},
                        "timelineItems": {"nodes": []},
                    }
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, tzinfo=UTC)

        metrics = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )

        assert metrics.total_prs == 0


@pytest.mark.asyncio
async def test_collect_pr_metrics_filters_by_date(
    collector: MetricsCollector,
) -> None:
    """Test that PRs are filtered by date range."""
    mock_data = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 1,
                        "title": "In range PR",
                        "url": "https://github.com/owner/repo/pull/1",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2024-01-10T12:00:00Z",
                        "updatedAt": "2024-01-15T12:00:00Z",
                        "closedAt": "2024-01-15T12:00:00Z",
                        "mergedAt": "2024-01-15T12:00:00Z",
                        "body": "",
                        "additions": 10,
                        "deletions": 5,
                        "changedFiles": 1,
                        "commits": {"totalCount": 1},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {"nodes": []},
                    },
                    {
                        "number": 2,
                        "title": "Out of range PR",
                        "url": "https://github.com/owner/repo/pull/2",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2023-12-10T12:00:00Z",
                        "updatedAt": "2023-12-15T12:00:00Z",
                        "closedAt": "2023-12-15T12:00:00Z",
                        "mergedAt": None,
                        "body": "",
                        "additions": 10,
                        "deletions": 5,
                        "changedFiles": 1,
                        "commits": {"totalCount": 1},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {"nodes": []},
                    },
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, tzinfo=UTC)

        metrics = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )

        # Only the PR within range should be collected
        assert metrics.total_prs == 1
        assert metrics.pull_requests[0].number == 1


@pytest.mark.asyncio
async def test_collect_pr_metrics_filters_by_base_branch(
    collector: MetricsCollector,
) -> None:
    """Test that PRs are filtered by base branch."""
    mock_data = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 1,
                        "title": "Main branch PR",
                        "url": "https://github.com/owner/repo/pull/1",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2024-01-10T12:00:00Z",
                        "updatedAt": "2024-01-15T12:00:00Z",
                        "closedAt": "2024-01-15T12:00:00Z",
                        "mergedAt": "2024-01-15T12:00:00Z",
                        "body": "",
                        "additions": 10,
                        "deletions": 5,
                        "changedFiles": 1,
                        "commits": {"totalCount": 1},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {"nodes": []},
                    },
                    {
                        "number": 2,
                        "title": "Develop branch PR",
                        "url": "https://github.com/owner/repo/pull/2",
                        "isDraft": False,
                        "baseRefName": "develop",
                        "createdAt": "2024-01-10T12:00:00Z",
                        "updatedAt": "2024-01-15T12:00:00Z",
                        "closedAt": "2024-01-15T12:00:00Z",
                        "mergedAt": "2024-01-15T12:00:00Z",
                        "body": "",
                        "additions": 20,
                        "deletions": 10,
                        "changedFiles": 2,
                        "commits": {"totalCount": 2},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {"nodes": []},
                    },
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, tzinfo=UTC)

        # Filter by main branch
        metrics_main = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
            base_branch="main",
        )

        assert metrics_main.total_prs == 1
        assert metrics_main.pull_requests[0].number == 1
        assert metrics_main.pull_requests[0].base_branch == "main"

        # Filter by develop branch
        metrics_develop = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
            base_branch="develop",
        )

        assert metrics_develop.total_prs == 1
        assert metrics_develop.pull_requests[0].number == 2
        assert metrics_develop.pull_requests[0].base_branch == "develop"

        # No filter - get all PRs
        metrics_all = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
            base_branch=None,
        )

        assert metrics_all.total_prs == 2


@pytest.mark.asyncio
async def test_collect_pr_metrics_handles_malformed_pr(
    collector: MetricsCollector,
) -> None:
    """Test that malformed PRs are skipped but collection continues."""
    mock_data = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 1,
                        "title": "Valid PR",
                        "url": "https://github.com/owner/repo/pull/1",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2024-01-10T12:00:00Z",
                        "updatedAt": "2024-01-15T12:00:00Z",
                        "closedAt": "2024-01-15T12:00:00Z",
                        "mergedAt": "2024-01-15T12:00:00Z",
                        "body": "",
                        "additions": 10,
                        "deletions": 5,
                        "changedFiles": 1,
                        "commits": {"totalCount": 1},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {"nodes": []},
                    },
                    {
                        "number": 2,
                        "title": "Malformed PR",
                        # Missing required fields like createdAt, closedAt
                        "isDraft": False,
                        "baseRefName": "main",
                        "author": {"login": "testuser"},
                    },
                    {
                        "number": 3,
                        "title": "Another Valid PR",
                        "url": "https://github.com/owner/repo/pull/3",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2024-01-20T12:00:00Z",
                        "updatedAt": "2024-01-25T12:00:00Z",
                        "closedAt": "2024-01-25T12:00:00Z",
                        "mergedAt": "2024-01-25T12:00:00Z",
                        "body": "",
                        "additions": 20,
                        "deletions": 10,
                        "changedFiles": 2,
                        "commits": {"totalCount": 2},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {"nodes": []},
                    },
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, tzinfo=UTC)

        metrics = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )

        # Should collect 2 valid PRs and skip the malformed one
        assert metrics.total_prs == 2
        assert len(metrics.pull_requests) == 2
        assert metrics.pull_requests[0].number == 1
        assert metrics.pull_requests[1].number == 3


@pytest.mark.asyncio
async def test_collect_pr_metrics_calculates_review_time_with_reopenings(
    collector: MetricsCollector,
) -> None:
    """Test that review time accounts for PR reopenings."""
    # PR created at 10:00, closed at 12:00 (2 hours open)
    # Then reopened at 14:00, closed again at 16:00 (2 more hours open)
    # Total review time should be 4 hours, not 6 hours (16:00 - 10:00)
    mock_data = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "number": 1,
                        "title": "PR with reopenings",
                        "url": "https://github.com/owner/repo/pull/1",
                        "isDraft": False,
                        "baseRefName": "main",
                        "createdAt": "2024-01-10T10:00:00Z",
                        "updatedAt": "2024-01-10T16:00:00Z",
                        "closedAt": "2024-01-10T16:00:00Z",
                        "mergedAt": "2024-01-10T16:00:00Z",
                        "body": "",
                        "additions": 10,
                        "deletions": 5,
                        "changedFiles": 1,
                        "commits": {"totalCount": 1},
                        "author": {"login": "testuser"},
                        "labels": {"nodes": []},
                        "comments": {"totalCount": 0},
                        "reviews": {"nodes": []},
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                        "timelineItems": {
                            "nodes": [
                                {
                                    "__typename": "ClosedEvent",
                                    "createdAt": "2024-01-10T12:00:00Z",
                                },
                                {
                                    "__typename": "ReopenedEvent",
                                    "createdAt": "2024-01-10T14:00:00Z",
                                },
                                {
                                    "__typename": "ClosedEvent",
                                    "createdAt": "2024-01-10T16:00:00Z",
                                },
                            ]
                        },
                    }
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, tzinfo=UTC)

        metrics = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )

        pr = metrics.pull_requests[0]
        # Should be 4 hours: 2 hours (10-12) + 2 hours (14-16)
        assert pr.review_time_hours == 4.0


@pytest.mark.asyncio
async def test_collect_pr_metrics_invalid_owner(collector: MetricsCollector) -> None:
    """Test that collect_pr_metrics raises ValueError for invalid owner format."""
    start_date = datetime(2024, 1, 1, tzinfo=UTC)
    end_date = datetime(2024, 1, 31, tzinfo=UTC)

    with pytest.raises(ValueError, match="Invalid owner"):
        await collector.collect_pr_metrics(
            owner="invalid@owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )


@pytest.mark.asyncio
async def test_collect_pr_metrics_invalid_repo(collector: MetricsCollector) -> None:
    """Test that collect_pr_metrics raises ValueError for invalid repo format."""
    start_date = datetime(2024, 1, 1, tzinfo=UTC)
    end_date = datetime(2024, 1, 31, tzinfo=UTC)

    with pytest.raises(ValueError, match="Invalid repo"):
        await collector.collect_pr_metrics(
            owner="owner",
            repo="invalid/repo",
            start_date=start_date,
            end_date=end_date,
        )
