"""Example usage of the github-metrics library."""

import asyncio
from datetime import UTC, datetime, timedelta

from github_metrics import MetricsCollector, analyze_pr_diff, get_settings


def on_progress(count: int, message: str) -> None:
    """Progress callback to show collection status."""
    print(f"   [{count} PRs] {message}")


async def main() -> None:
    """
    Example of collecting PR metrics from a GitHub repository.

    Before running:
    1. Set GITHUB_METRICS__GITHUB_TOKEN environment variable
    2. Update owner and repo variables below
    """
    # Get settings (reads from environment variables)
    settings = get_settings()

    # Initialize the metrics collector with async context manager
    async with MetricsCollector(settings) as collector:
        # Define the time period for metrics collection
        # Example: last 7 days
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=7)

        # Repository to collect metrics from
        # Update these with your repository details
        owner = "cryptoboyio"  # e.g., "octocat"
        repo = "qa_tests"  # e.g., "Hello-World"

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
            # Collect metrics with progress tracking
            # Use max_results to limit collection (useful for large repos)
            # Use progress_callback to track progress during collection
            metrics = await collector.collect_pr_metrics(
                owner=owner,
                repo=repo,
                start_date=start_date,
                end_date=end_date,
                base_branch=base_branch,
                max_results=50,  # Limit to 50 PRs (set to None for all)
                progress_callback=on_progress,
            )

            # Display summary
            print(f"\n📊 Summary for {metrics.repository}")
            print(f"   Total PRs closed: {metrics.total_prs}")
            print(f"   ✅ Merged: {metrics.merged_prs}")
            print(f"   ❌ Closed (not merged): {metrics.closed_prs}")

            if metrics.total_prs > 0:
                # Calculate average metrics
                avg_changes = sum(
                    pr.changes_count for pr in metrics.pull_requests
                ) / len(metrics.pull_requests)
                avg_review_time = sum(
                    pr.review_time_hours for pr in metrics.pull_requests
                ) / len(metrics.pull_requests)
                avg_comments = sum(
                    pr.comments_count for pr in metrics.pull_requests
                ) / len(metrics.pull_requests)

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
                    print(f"   - Additions: +{pr.additions_count} lines")
                    print(f"   - Deletions: -{pr.deletions_count} lines")
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

                # Analyze test changes in each PR
                print("\n" + "=" * 60)
                print("📋 Test Analyzer - Analyzing test changes in PRs")
                print("=" * 60)

                total_new_tests = 0
                total_updated_tests = 0

                for pr in metrics.pull_requests:
                    try:
                        # Fetch the actual diff for this PR
                        diff_text = await collector.get_pr_diff(
                            owner=owner,
                            repo=repo,
                            pr_number=pr.number,
                        )

                        # Analyze the diff for test changes
                        test_results = analyze_pr_diff(diff_text)

                        if test_results.total_new > 0 or test_results.total_updated > 0:
                            print(f"\nPR #{pr.number}: {pr.title}")

                            if test_results.new_tests:
                                print(f"   ✨ New tests ({test_results.total_new}):")
                                for test in test_results.new_tests:
                                    print(f"      + {test.filename}::{test.test_name}")

                            if test_results.updated_tests:
                                count = test_results.total_updated
                                print(f"   🔄 Updated tests ({count}):")
                                for test in test_results.updated_tests:
                                    print(f"      ~ {test.filename}::{test.test_name}")

                            total_new_tests += test_results.total_new
                            total_updated_tests += test_results.total_updated

                    except Exception as e:
                        print(f"\n   ⚠️ Could not analyze PR #{pr.number}: {e}")

                print("\n" + "-" * 60)
                print(
                    f"📊 Test Changes Summary: {total_new_tests} new tests, "
                    f"{total_updated_tests} updated tests"
                )

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


if __name__ == "__main__":
    asyncio.run(main())
