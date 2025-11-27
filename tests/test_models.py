"""Tests for data models."""

from datetime import UTC, datetime

from github_metrics.models import PRMetrics, PRResolution, RepositoryMetrics, User


def test_user_model() -> None:
    """Test User model."""
    user = User(login="testuser", name="Test User")
    assert user.login == "testuser"
    assert user.name == "Test User"


def test_user_model_without_name() -> None:
    """Test User model without name."""
    user = User(login="testuser", name=None)
    assert user.login == "testuser"
    assert user.name is None


def test_pr_resolution_enum() -> None:
    """Test PRResolution enum."""
    assert PRResolution.MERGED.value == "merged"
    assert PRResolution.CLOSED_NOT_MERGED.value == "closed_not_merged"


def test_pr_metrics_model() -> None:
    """Test PRMetrics model."""
    created = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    closed = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)
    merged = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)

    author = User(login="author", name="Author Name")
    approver = User(login="approver", name="Approver Name")

    pr = PRMetrics(
        number=123,
        title="Test PR",
        url="https://github.com/owner/repo/pull/123",
        base_branch="main",
        author=author,
        created_at=created,
        closed_at=closed,
        merged_at=merged,
        resolution=PRResolution.MERGED,
        changes_count=150,
        additions_count=100,
        deletions_count=50,
        review_time_hours=24.0,
        commits_count=5,
        review_comments_count=3,
        comments_count=2,
        approvers=[approver],
        commenters=[],
        labels=["bug", "enhancement"],
        description="This is a test PR",
        test_metrics=None,
    )

    assert pr.number == 123
    assert pr.title == "Test PR"
    assert pr.author.login == "author"
    assert pr.resolution == PRResolution.MERGED
    assert pr.changes_count == 150
    assert pr.additions_count == 100
    assert pr.deletions_count == 50
    assert pr.review_time_hours == 24.0
    assert len(pr.approvers) == 1
    assert pr.approvers[0].login == "approver"
    assert len(pr.labels) == 2


def test_repository_metrics_model() -> None:
    """Test RepositoryMetrics model."""
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 31, tzinfo=UTC)

    created1 = datetime(2024, 1, 10, 12, 0, 0, tzinfo=UTC)
    closed1 = datetime(2024, 1, 11, 12, 0, 0, tzinfo=UTC)
    merged1 = datetime(2024, 1, 11, 12, 0, 0, tzinfo=UTC)

    created2 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    closed2 = datetime(2024, 1, 16, 12, 0, 0, tzinfo=UTC)

    author = User(login="author", name=None)

    pr1 = PRMetrics(
        number=1,
        title="PR 1",
        url="https://github.com/owner/repo/pull/1",
        base_branch="main",
        author=author,
        created_at=created1,
        closed_at=closed1,
        merged_at=merged1,
        resolution=PRResolution.MERGED,
        changes_count=100,
        additions_count=70,
        deletions_count=30,
        review_time_hours=24.0,
        commits_count=3,
        review_comments_count=2,
        comments_count=1,
        test_metrics=None,
    )

    pr2 = PRMetrics(
        number=2,
        title="PR 2",
        url="https://github.com/owner/repo/pull/2",
        base_branch="develop",
        author=author,
        created_at=created2,
        closed_at=closed2,
        merged_at=None,
        resolution=PRResolution.CLOSED_NOT_MERGED,
        changes_count=50,
        additions_count=30,
        deletions_count=20,
        review_time_hours=24.0,
        commits_count=2,
        review_comments_count=1,
        comments_count=0,
        test_metrics=None,
    )

    metrics = RepositoryMetrics(
        repository="owner/repo",
        period_start=start,
        period_end=end,
        pull_requests=[pr1, pr2],
    )

    assert metrics.repository == "owner/repo"
    assert metrics.total_prs == 2
    assert metrics.merged_prs == 1
    assert metrics.closed_prs == 1
    assert len(metrics.pull_requests) == 2
