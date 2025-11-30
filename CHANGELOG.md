# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Async context manager support for `MetricsCollector` and `GitHubGraphQLClient`
- Test analyzer module for analyzing pytest changes in PR diffs (`analyze_pr_diff`)
- `PytestInfo` and `PytestMetrics` models for test change analysis
- `max_results` parameter to `collect_pr_metrics()` for pagination control
- `progress_callback` parameter to `collect_pr_metrics()` for progress reporting
- `ProgressCallback` type alias exported for type hints
- `get_pr_diff()` method to fetch PR diffs from GitHub API for test analysis

### Changed

- `github_token` setting now uses `SecretStr` for improved security
- `get_settings()` now caches the settings singleton using `lru_cache`
- Owner/repo validation now allows dots in names (e.g., `docker.github.io`)

### Removed

- `print_results()` function - use `analyze_pr_diff()` and access results directly

### Fixed

- Unused variable warning in tests

## [0.1.0] - 2024-01-01

### Added

- Initial release
- `MetricsCollector` for collecting GitHub PR metrics
- `GitHubGraphQLClient` for GitHub GraphQL API access
- Support for time-based and branch-based filtering
- Automatic rate limit handling with exponential backoff
- Pydantic models for PR metrics (`PRMetrics`, `RepositoryMetrics`, `User`)
- Configuration via environment variables using `pydantic-settings`
- Comprehensive test suite

[Unreleased]: https://github.com/l0kifs/github-metrics/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/l0kifs/github-metrics/releases/tag/v0.1.0
