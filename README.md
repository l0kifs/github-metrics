# github-metrics

Asynchronous library for collecting GitHub metrics using GraphQL API.

## Description

`github-metrics` is a Python library for collecting metrics on Pull Requests from GitHub repositories. The library uses GitHub GraphQL API for efficient data retrieval and fully supports asynchronous operations.

## Key Features

- **Asynchronous metrics collection**: Full support for async/await
- **GitHub GraphQL API**: Using efficient GraphQL API instead of REST
- **Time-based filtering**: Collect metrics for a specified time period
- **Branch filtering**: Ability to filter PRs by target branch (main, develop, etc.)
- **Detailed PR information**: 
  - Target branch (base branch)
  - Number of changes (additions + deletions)
  - Number of added lines (additions)
  - Number of deleted lines (deletions)
  - Time spent in review
  - Number of commits
  - Number of comments and review comments
  - List of users who approved
  - List of users who left comments
  - PR labels
  - Full PR description
- **Resolution separation**: Merged vs Closed (not merged)
- **Draft PR exclusion**: Draft PRs are not included in metrics

## Technical Stack

- **Python**: 3.12+
- **httpx**: Asynchronous HTTP client
- **loguru**: Structured logging
- **pydantic**: Data validation and settings
- **pydantic-settings**: Configuration management

## Installation

```bash
pip install github-metrics
```

Or for development:

```bash
git clone https://github.com/l0kifs/github-metrics.git
cd github-metrics
uv sync --all-groups
```

## Configuration

The library uses environment variables for configuration. Create a `.env` file or set environment variables:

```bash
# Required
GITHUB_METRICS__GITHUB_TOKEN=your_github_personal_access_token

# Optional
GITHUB_METRICS__GITHUB_API_URL=https://api.github.com/graphql  # GitHub GraphQL API URL
GITHUB_METRICS__GITHUB_API_TIMEOUT=120.0  # API request timeout in seconds
GITHUB_METRICS__GITHUB_PAGE_SIZE=100  # Items per page in API requests
GITHUB_METRICS__LOGGING_LEVEL=INFO  # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Getting GitHub Token

1. Go to Settings → Developer settings → Personal access tokens
2. Create a new token with permissions:
   - `repo` (full access to private repositories) or
   - `public_repo` (access only to public repositories)

## Usage

### Basic Example

```python
import asyncio
from datetime import UTC, datetime, timedelta
from github_metrics import MetricsCollector, get_settings

async def main():
    # Get settings (from environment variables)
    settings = get_settings()
    
    # Initialize the collector with async context manager
    async with MetricsCollector(settings) as collector:
        # Define the time period (e.g., last 30 days)
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=30)
        
        # Collect metrics
        # You can specify a target branch (base_branch) for filtering
        # For example: base_branch="main" or base_branch="develop"
        metrics = await collector.collect_pr_metrics(
            owner="octocat",
            repo="Hello-World",
            start_date=start_date,
            end_date=end_date,
            base_branch=None,  # None = all branches
        )
        
        # Use the results
        print(f"Total PRs: {metrics.total_prs}")
        print(f"Merged PRs: {metrics.merged_prs}")
        print(f"Closed (not merged) PRs: {metrics.closed_prs}")
        
        for pr in metrics.pull_requests:
            print(f"PR #{pr.number}: {pr.title}")
            print(f"  Resolution: {pr.resolution}")
            print(f"  Changes: {pr.changes_count}")
            print(f"  Review time: {pr.review_time_hours:.2f} hours")
            print(f"  Approvers: {[u.login for u in pr.approvers]}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Limiting Results

For large repositories, you can limit the number of results:

```python
# Limit to first 50 PRs
metrics = await collector.collect_pr_metrics(
    owner="octocat",
    repo="Hello-World",
    start_date=start_date,
    end_date=end_date,
    max_results=50,  # Stop after collecting 50 PRs
)
```

### Progress Tracking

For long-running collections, you can provide a callback to track progress:

```python
def on_progress(count: int, message: str) -> None:
    print(f"[{count} PRs] {message}")

metrics = await collector.collect_pr_metrics(
    owner="octocat",
    repo="Hello-World",
    start_date=start_date,
    end_date=end_date,
    progress_callback=on_progress,
)

# Output:
# [0 PRs] Starting collection for octocat/Hello-World
# [0 PRs] Fetching page 1...
# [25 PRs] Fetching page 2...
# [42 PRs] Collection complete. Found 42 PRs.
```

For a complete working example with detailed output and JSON export, see `examples/example.py`.

### Working with Data Models

```python
from github_metrics.models import PRMetrics, PRResolution, RepositoryMetrics

# Metrics for repository contains list of all PRs
for pr in metrics.pull_requests:
    # Basic information
    print(pr.number, pr.title, pr.url)
    print(f"Target branch: {pr.base_branch}")
    print(pr.author.login, pr.author.name)
    
    # Dates
    print(pr.created_at, pr.closed_at, pr.merged_at)
    
    # Resolution
    if pr.resolution == PRResolution.MERGED:
        print("PR was merged")
    else:
        print("PR was closed without merge")
    
    # Metrics
    print(f"Changes: {pr.changes_count}")
    print(f"Lines added: {pr.additions_count}")
    print(f"Lines deleted: {pr.deletions_count}")
    print(f"Review time: {pr.review_time_hours} hours")
    print(f"Commits: {pr.commits_count}")
    print(f"Comments: {pr.comments_count}")
    print(f"Review comments: {pr.review_comments_count}")
    
    # Participants
    print(f"Approvers: {[u.login for u in pr.approvers]}")
    print(f"Commenters: {[u.login for u in pr.commenters]}")
    
    # Additional information
    print(f"Labels: {pr.labels}")
    print(f"Description: {pr.description}")
```

## Data Models

### `User`
GitHub user information:
- `login: str` - username
- `name: Optional[str]` - display name

### `PRMetrics`
Metrics for a single Pull Request:
- `number: int` - PR number
- `title: str` - PR title
- `url: str` - PR URL
- `base_branch: str` - PR target branch
- `author: User` - PR author
- `created_at: datetime` - creation date
- `closed_at: datetime` - closure date
- `merged_at: Optional[datetime]` - merge date (if merged)
- `resolution: PRResolution` - final resolution
- `changes_count: int` - number of changes (additions + deletions)
- `additions_count: int` - number of added lines
- `deletions_count: int` - number of deleted lines
- `review_time_hours: float` - time in review (hours)
- `commits_count: int` - number of commits
- `review_comments_count: int` - number of review comments
- `comments_count: int` - number of general comments
- `approvers: list[User]` - users who approved
- `commenters: list[User]` - users who left comments
- `labels: list[str]` - PR labels
- `description: str` - full PR description

### `RepositoryMetrics`
Aggregated metrics for a repository:
- `repository: str` - repository name (owner/repo)
- `period_start: datetime` - period start
- `period_end: datetime` - period end
- `pull_requests: list[PRMetrics]` - list of PR metrics
- `total_prs: int` - total number of PRs (property)
- `merged_prs: int` - number of merged PRs (property)
- `closed_prs: int` - number of closed without merge PRs (property)

### `PRResolution`
Enum of PR final resolution:
- `MERGED` - PR was merged
- `CLOSED_NOT_MERGED` - PR was closed without merge

### `PytestInfo`
Information about a single test function:
- `filename: str` - path to the test file
- `test_name: str` - name of the test function

### `PytestMetrics`
Metrics for test changes in a PR diff:
- `new_tests: list[PytestInfo]` - list of newly added tests
- `updated_tests: list[PytestInfo]` - list of updated/modified tests
- `total_new: int` - total number of new tests (property)
- `total_updated: int` - total number of updated tests (property)

## Test Analyzer

The library includes a utility for analyzing pytest test changes in PR diffs:

```python
from github_metrics import MetricsCollector, analyze_pr_diff, get_settings

async def analyze_tests_in_prs():
    settings = get_settings()
    
    async with MetricsCollector(settings) as collector:
        # First collect PR metrics
        metrics = await collector.collect_pr_metrics(
            owner="octocat",
            repo="Hello-World",
            start_date=start_date,
            end_date=end_date,
        )
        
        # Then fetch and analyze diffs for each PR
        for pr in metrics.pull_requests:
            # Fetch the actual diff from GitHub
            diff_text = await collector.get_pr_diff(
                owner="octocat",
                repo="Hello-World",
                pr_number=pr.number,
            )
            
            # Analyze the diff for test changes
            results = analyze_pr_diff(diff_text)
            
            if results.total_new > 0 or results.total_updated > 0:
                print(f"PR #{pr.number}: {pr.title}")
                for test in results.new_tests:
                    print(f"  + New: {test.filename}::{test.test_name}")
                for test in results.updated_tests:
                    print(f"  ~ Updated: {test.filename}::{test.test_name}")
```

## Development

### Installing Development Dependencies

```bash
uv sync --all-groups
```

### Running Tests

```bash
uv run pytest tests/ -v
```

### Linting and Formatting

```bash
# Check code
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/

# Type checking
uv run mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) file

## Authors

- l0kifs - [l0kifs91@gmail.com](mailto:l0kifs91@gmail.com)

## Links

- [GitHub Repository](https://github.com/l0kifs/github-metrics)
- [Issue Tracker](https://github.com/l0kifs/github-metrics/issues)
- [GitHub GraphQL API Documentation](https://docs.github.com/en/graphql)