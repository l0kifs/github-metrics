"""Data models for GitHub metrics."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PRResolution(str, Enum):
    """PR final resolution types."""

    MERGED = "merged"
    CLOSED_NOT_MERGED = "closed_not_merged"


class User(BaseModel):
    """GitHub user information."""

    login: str = Field(..., description="GitHub username")
    name: str | None = Field(None, description="User's display name")


class PRMetrics(BaseModel):
    """Metrics for a single pull request."""

    # Basic PR info
    number: int = Field(..., description="PR number")
    title: str = Field(..., description="PR title")
    url: str = Field(..., description="PR URL")
    base_branch: str = Field(..., description="Target branch for the PR")
    author: User = Field(..., description="PR author")
    created_at: datetime = Field(..., description="PR creation timestamp")
    closed_at: datetime = Field(..., description="PR closure timestamp")
    merged_at: datetime | None = Field(None, description="PR merge timestamp")

    # Resolution
    resolution: PRResolution = Field(
        ..., description="Final resolution (merged or closed without merge)"
    )

    # Metrics
    changes_count: int = Field(
        ..., description="Total number of changes (additions + deletions)"
    )
    review_time_hours: float = Field(..., description="Time spent in review (hours)")
    commits_count: int = Field(..., description="Number of commits in the PR")
    review_comments_count: int = Field(..., description="Number of review comments")
    comments_count: int = Field(..., description="Number of general comments")

    # Participants
    approvers: list[User] = Field(
        default_factory=list, description="Users who approved the PR"
    )
    commenters: list[User] = Field(
        default_factory=list, description="Users who left comments on the PR"
    )

    # Additional info
    labels: list[str] = Field(default_factory=list, description="PR labels")
    description: str = Field(default="", description="Full PR description")


class RepositoryMetrics(BaseModel):
    """Aggregated metrics for a repository."""

    repository: str = Field(..., description="Repository name (owner/repo)")
    period_start: datetime = Field(..., description="Start of the metrics period")
    period_end: datetime = Field(..., description="End of the metrics period")
    pull_requests: list[PRMetrics] = Field(
        default_factory=list, description="List of PR metrics"
    )

    @property
    def total_prs(self) -> int:
        """Total number of PRs."""
        return len(self.pull_requests)

    @property
    def merged_prs(self) -> int:
        """Number of merged PRs."""
        return sum(
            1 for pr in self.pull_requests if pr.resolution == PRResolution.MERGED
        )

    @property
    def closed_prs(self) -> int:
        """Number of closed but not merged PRs."""
        return sum(
            1
            for pr in self.pull_requests
            if pr.resolution == PRResolution.CLOSED_NOT_MERGED
        )


class PytestInfo(BaseModel):
    """Information about a single test function."""

    filename: str = Field(..., description="Path to the test file")
    test_name: str = Field(..., description="Name of the test function")


class PytestMetrics(BaseModel):
    """Metrics for test changes in a PR diff."""

    new_tests: list[PytestInfo] = Field(
        default_factory=list, description="List of newly added tests"
    )
    updated_tests: list[PytestInfo] = Field(
        default_factory=list, description="List of updated/modified tests"
    )

    @property
    def total_new(self) -> int:
        """Total number of new tests."""
        return len(self.new_tests)

    @property
    def total_updated(self) -> int:
        """Total number of updated tests."""
        return len(self.updated_tests)
