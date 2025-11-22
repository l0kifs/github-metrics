"""Example usage of the github-metrics library."""

import asyncio
from datetime import UTC, datetime, timedelta

from github_metrics import MetricsCollector, get_settings


async def main() -> None:
    """
    Example of collecting PR metrics from a GitHub repository.

    Before running:
    1. Set GITHUB_METRICS__GITHUB_TOKEN environment variable
    2. Update owner and repo variables below
    """
    # Get settings (reads from environment variables)
    settings = get_settings()

    # Initialize the metrics collector
    collector = MetricsCollector(settings)

    # Define the time period for metrics collection
    # Example: last 7 days
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=7)

    # Repository to collect metrics from
    # Update these with your repository details
    owner = "octocat"  # e.g., "octocat"
    repo = "Hello-World"  # e.g., "Hello-World"

    # Optional: filter by target branch
    # Set to None to collect PRs for all branches
    # Set to specific branch name (e.g., "main", "develop") to filter
    base_branch = None  # e.g., "main" or "develop"

    print(f"\nCollecting PR metrics for {owner}/{repo}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    if base_branch:
        print(f"Target branch: {base_branch}")
    print("-" * 60)

    try:
        # Collect metrics
        metrics = await collector.collect_pr_metrics(
            owner=owner,
            repo=repo,
            start_date=start_date,
            end_date=end_date,
            base_branch=base_branch,
        )

        # Display summary
        print(f"\n📊 Summary for {metrics.repository}")
        print(f"   Total PRs closed: {metrics.total_prs}")
        print(f"   ✅ Merged: {metrics.merged_prs}")
        print(f"   ❌ Closed (not merged): {metrics.closed_prs}")

        if metrics.total_prs > 0:
            # Calculate average metrics
            avg_changes = sum(pr.changes_count for pr in metrics.pull_requests) / len(
                metrics.pull_requests
            )
            avg_review_time = sum(
                pr.review_time_hours for pr in metrics.pull_requests
            ) / len(metrics.pull_requests)
            avg_comments = sum(pr.comments_count for pr in metrics.pull_requests) / len(
                metrics.pull_requests
            )

            print("\n📈 Average Metrics:")
            print(f"   Changes per PR: {avg_changes:.0f}")
            print(f"   Review time: {avg_review_time:.1f} hours")
            print(f"   Comments per PR: {avg_comments:.1f}")

            # Display detailed PR information
            print("\n📝 Detailed PR Information:")
            print("-" * 60)

            for pr in metrics.pull_requests:
                print(f"\nPR #{pr.number}: {pr.title}")
                print(f"   URL: {pr.url}")
                print(f"   Author: {pr.author.login}")
                print(f"   Status: {pr.resolution.value}")
                print(f"   Created: {pr.created_at.strftime('%Y-%m-%d %H:%M')}")
                print(f"   Closed: {pr.closed_at.strftime('%Y-%m-%d %H:%M')}")

                print("\n   Metrics:")
                print(f"   - Changes: {pr.changes_count} lines")
                print(f"   - Commits: {pr.commits_count}")
                print(f"   - Review time: {pr.review_time_hours:.1f} hours")
                print(f"   - Comments: {pr.comments_count}")
                print(f"   - Review comments: {pr.review_comments_count}")

                if pr.approvers:
                    approver_logins = [u.login for u in pr.approvers]
                    print(f"   - Approvers: {', '.join(approver_logins)}")

                if pr.commenters:
                    commenter_logins = [u.login for u in pr.commenters]
                    print(f"   - Commenters: {', '.join(commenter_logins)}")

                if pr.labels:
                    print(f"   - Labels: {', '.join(pr.labels)}")

                if pr.description:
                    # Show first 100 characters of description
                    desc_preview = pr.description[:100]
                    if len(pr.description) > 100:
                        desc_preview += "..."
                    print(f"   - Description: {desc_preview}")

            # Export metrics to JSON (optional)
            import json

            output_file = f"metrics_{owner}_{repo}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    metrics.model_dump(mode="json"),
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            print(f"\n💾 Metrics exported to {output_file}")

        else:
            print("\nNo PRs found in the specified time period.")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. GITHUB_METRICS__GITHUB_TOKEN is set correctly")
        print("2. The token has required permissions (repo or public_repo)")
        print("3. The repository owner and name are correct")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise

    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
