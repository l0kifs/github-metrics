"""
Analyze pytest test changes in a GitHub PR.
Identifies new tests vs updated tests based on git diff.

A test is NEW if ALL lines (from first decorator to end of function) are additions (+).
A test is UPDATED if ANY line is removed (-) or unchanged ( ).
"""

import re

from github_metrics.models import PytestInfo, PytestMetrics


def analyze_pr_diff(diff_text: str) -> PytestMetrics:
    """
    Analyze unified diff to find new and updated test functions.

    Args:
        diff_text: Unified diff from GitHub API (raw diff format)

    Returns:
        PytestMetrics containing lists of new and updated tests
    """
    new_tests: list[PytestInfo] = []
    updated_tests: list[PytestInfo] = []

    # Split diff into individual file diffs
    file_diffs = re.split(r"^diff --git ", diff_text, flags=re.MULTILINE)[1:]

    for file_diff in file_diffs:
        # Extract filename
        match = re.search(r"^a/(.*?) b/", file_diff)
        if not match:
            continue

        filename = match.group(1)

        # Only process test files
        if not ("test" in filename and filename.endswith(".py")):
            continue

        # Check if file is completely new
        if re.search(r"^new file mode", file_diff, re.MULTILINE):
            # All tests in new file are new
            for test_match in re.finditer(
                r"^\+.*def (test_\w+)", file_diff, re.MULTILINE
            ):
                new_tests.append(
                    PytestInfo(filename=filename, test_name=test_match.group(1))
                )
            continue

        # For modified files, analyze each test function
        test_statuses = _find_tests_in_diff(file_diff)

        for test_name, is_new in test_statuses.items():
            if is_new:
                new_tests.append(PytestInfo(filename=filename, test_name=test_name))
            else:
                updated_tests.append(PytestInfo(filename=filename, test_name=test_name))

    return PytestMetrics(new_tests=new_tests, updated_tests=updated_tests)


def _find_tests_in_diff(file_diff: str) -> dict[str, bool]:
    """
    Find test functions and determine if they're new or updated.

    Simple logic:
    - Find each test function (def test_*)
    - Collect all lines from first decorator (or function def) to end of function
    - If ALL lines are additions (+), it's NEW
    - If ANY line is removal (-) or unchanged ( ), it's UPDATED

    Returns:
        Dictionary mapping test_name -> is_new (True if new, False if updated)
    """
    lines = file_diff.split("\n")
    test_statuses: dict[str, bool] = {}

    i = 0
    while i < len(lines):
        line = lines[i]

        # Found a test function definition
        if re.search(r"^[+\- ].*def (test_\w+)", line):
            match = re.search(r"def (test_\w+)", line)
            if match:
                test_name = match.group(1)

                # Collect all lines for this test
                test_lines = _extract_test_lines(lines, i)

                # Check if ALL lines are additions
                is_new = all(
                    ln.startswith("+")
                    for ln in test_lines
                    if ln.strip()
                    and not ln.startswith("+++")  # Ignore empty lines and metadata
                )

                test_statuses[test_name] = is_new

        i += 1

    return test_statuses


def _extract_test_lines(lines: list[str], func_idx: int) -> list[str]:
    """
    Extract all lines belonging to a test function.
    Goes backwards to find decorators, forwards to find function body.
    """
    test_lines: list[str] = []

    # Go backwards to find decorators
    idx = func_idx - 1
    while idx >= 0:
        line = lines[idx]

        # Stop if we hit another function/class or non-decorator content
        if re.match(r"^[+\- ](def |class |@)", line):
            if "@" in line:
                test_lines.insert(0, line)
                idx -= 1
                continue
            else:
                break

        # Stop at empty lines that aren't part of decorator block
        if not line.strip() or line in ["---", "+++"]:
            break

        idx -= 1

    # Add the function definition line
    test_lines.append(lines[func_idx])

    # Go forwards to get function body
    idx = func_idx + 1
    indent_level: int | None = None

    while idx < len(lines):
        line = lines[idx]

        # Skip diff metadata
        if line.startswith("@@") or line.startswith("+++") or line.startswith("---"):
            idx += 1
            continue

        # Detect function end: next function/class definition at same or lower indent
        if re.match(r"^[+\- ](def |class )", line):
            # Check if it's at the same or lower indentation level
            if indent_level is not None:
                current_indent = len(line) - len(line.lstrip("+- "))
                if current_indent <= indent_level:
                    break
            else:
                break

        # Set indent level from first body line
        if indent_level is None and line.strip() and not line.startswith("@@"):
            stripped = line.lstrip("+- ")
            if stripped.strip():
                indent_level = len(line) - len(stripped)

        test_lines.append(line)
        idx += 1

        # Safety: stop after reasonable function length
        if len(test_lines) > 200:
            break

    return test_lines

