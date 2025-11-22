"""Tests for metrics collector."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_metrics.collector import MetricsCollector
from github_metrics.config.settings import Settings
from github_metrics.models import PRResolution


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        github_token="test_token",
        github_api_url="https://api.github.com/graphql",
    )


@pytest.fixture
def collector(settings):
    """Create test collector."""
    return MetricsCollector(settings)


@pytest.mark.asyncio
async def test_collect_pr_metrics_basic(collector):
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
                        "createdAt": "2024-01-10T12:00:00Z",
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
                    }
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

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
        assert pr.resolution == PRResolution.MERGED
        assert pr.changes_count == 150
        assert pr.commits_count == 3
        assert len(pr.approvers) == 1
        assert pr.approvers[0].login == "reviewer"


@pytest.mark.asyncio
async def test_collect_pr_metrics_skips_drafts(collector):
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
                        "createdAt": "2024-01-10T12:00:00Z",
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
                        "reviewThreads": {"totalCount": 0, "nodes": []},
                    }
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        metrics = await collector.collect_pr_metrics(
            owner="owner",
            repo="repo",
            start_date=start_date,
            end_date=end_date,
        )

        assert metrics.total_prs == 0


@pytest.mark.asyncio
async def test_collect_pr_metrics_filters_by_date(collector):
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
                        "createdAt": "2024-01-10T12:00:00Z",
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
                    },
                    {
                        "number": 2,
                        "title": "Out of range PR",
                        "url": "https://github.com/owner/repo/pull/2",
                        "isDraft": False,
                        "createdAt": "2023-12-10T12:00:00Z",
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
                    },
                ],
            }
        }
    }

    with patch.object(
        collector.client, "execute_query", new=AsyncMock(return_value=mock_data)
    ):
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

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
async def test_parse_pr_metrics_closed_not_merged(collector):
    """Test parsing PR that was closed but not merged."""
    pr_node = {
        "number": 1,
        "title": "Test PR",
        "url": "https://github.com/owner/repo/pull/1",
        "isDraft": False,
        "createdAt": "2024-01-10T12:00:00Z",
        "closedAt": "2024-01-11T12:00:00Z",
        "mergedAt": None,
        "body": "Test",
        "additions": 50,
        "deletions": 25,
        "changedFiles": 3,
        "commits": {"totalCount": 2},
        "author": {"login": "testuser", "name": "Test User"},
        "labels": {"nodes": []},
        "comments": {"totalCount": 1},
        "reviews": {"nodes": []},
        "reviewThreads": {"totalCount": 0, "nodes": []},
    }

    pr_metrics = collector._parse_pr_metrics(pr_node)

    assert pr_metrics.number == 1
    assert pr_metrics.resolution == PRResolution.CLOSED_NOT_MERGED
    assert pr_metrics.merged_at is None
    assert pr_metrics.changes_count == 75
