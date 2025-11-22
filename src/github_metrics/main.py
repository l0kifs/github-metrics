"""Example usage of github-metrics library."""

import asyncio
from datetime import datetime, timedelta

from github_metrics import MetricsCollector, get_settings
from github_metrics.config.logging import setup_logging


async def main() -> None:
    """Example of collecting PR metrics."""
    setup_logging()

    # Get settings (GitHub token should be set via environment)
    settings = get_settings()

    # Initialize collector
    collector = MetricsCollector(settings)

    # Define time period (last 30 days)
    from datetime import timezone

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)

    # Example: Collect metrics for a repository
    # Replace with actual owner/repo
    owner = "owner"
    repo = "repo"

    try:
        metrics = await collector.collect_pr_metrics(
            owner=owner,
            repo=repo,
            start_date=start_date,
            end_date=end_date,
        )

        print(f"\nMetrics for {metrics.repository}")
        print(f"Period: {metrics.period_start} to {metrics.period_end}")
        print(f"Total PRs: {metrics.total_prs}")
        print(f"Merged PRs: {metrics.merged_prs}")
        print(f"Closed (not merged) PRs: {metrics.closed_prs}")
        print("\nPR Details:")
        for pr in metrics.pull_requests:
            print(f"  - PR #{pr.number}: {pr.title}")
            print(f"    Resolution: {pr.resolution}")
            print(f"    Changes: {pr.changes_count}")
            print(f"    Review time: {pr.review_time_hours:.2f} hours")
            print(f"    Comments: {pr.comments_count}")
            print(f"    Review comments: {pr.review_comments_count}")
            print(f"    Approvers: {[u.login for u in pr.approvers]}")
            print(f"    Labels: {pr.labels}")
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
