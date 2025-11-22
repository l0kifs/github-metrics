"""GraphQL queries for GitHub API."""

# Query to fetch closed pull requests for a repository
PULL_REQUESTS_QUERY = """
query GetPullRequests(
    $owner: String!
    $repo: String!
    $states: [PullRequestState!]
    $after: String
    $first: Int = 100
) {
    repository(owner: $owner, name: $repo) {
        pullRequests(
            states: $states
            first: $first
            after: $after
            orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
            pageInfo {
                hasNextPage
                endCursor
            }
            nodes {
                number
                title
                url
                isDraft
                baseRefName
                createdAt
                updatedAt
                closedAt
                mergedAt
                body
                additions
                deletions
                changedFiles
                commits {
                    totalCount
                }
                author {
                    login
                    ... on User {
                        name
                    }
                }
                labels(first: 100) {
                    nodes {
                        name
                    }
                }
                comments {
                    totalCount
                }
                reviews(first: 100) {
                    nodes {
                        author {
                            login
                            ... on User {
                                name
                            }
                        }
                        state
                    }
                }
                reviewThreads(first: 100) {
                    totalCount
                    nodes {
                        comments {
                            totalCount
                        }
                    }
                }
            }
        }
    }
}
"""
