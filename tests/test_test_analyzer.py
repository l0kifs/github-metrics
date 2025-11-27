"""Tests for test analyzer module."""

from github_metrics.models import PytestInfo, PytestMetrics
from github_metrics.test_analyzer import analyze_pr_diff


def test_analyze_new_test_in_modified_file() -> None:
    """Test detection of a new test in a modified file."""
    diff_text = """diff --git a/tests/test_api.py b/tests/test_api.py
index 1234567..abcdefg 100644
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -10,6 +10,15 @@ def test_existing():
     assert response.status_code == 200

+@pytest.mark.smoke
+@pytest.mark.api
+def test_new_endpoint():
+    \"\"\"Test new API endpoint.\"\"\"
+    response = client.get('/new')
+    assert response.status_code == 200
+    assert 'data' in response.json()
+
"""

    result = analyze_pr_diff(diff_text)

    assert len(result.new_tests) == 1
    assert result.new_tests[0].filename == "tests/test_api.py"
    assert result.new_tests[0].test_name == "test_new_endpoint"
    assert len(result.updated_tests) == 0


def test_analyze_updated_test() -> None:
    """Test detection of an updated test."""
    diff_text = """diff --git a/tests/test_api.py b/tests/test_api.py
index 1234567..abcdefg 100644
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -10,6 +10,8 @@ def test_existing():
     assert response.status_code == 200

 def test_old_function():
-    assert 1 == 1
+    # Updated implementation
+    assert 1 == 1
+    assert 2 == 2
"""

    result = analyze_pr_diff(diff_text)

    assert len(result.new_tests) == 0
    assert len(result.updated_tests) == 1
    assert result.updated_tests[0].filename == "tests/test_api.py"
    assert result.updated_tests[0].test_name == "test_old_function"


def test_analyze_new_and_updated_tests() -> None:
    """Test detection of both new and updated tests in same file."""
    diff_text = """diff --git a/tests/test_api.py b/tests/test_api.py
index 1234567..abcdefg 100644
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -10,6 +10,15 @@ def test_existing():
     assert response.status_code == 200

+@pytest.mark.smoke
+@pytest.mark.api
+def test_new_endpoint():
+    \"\"\"Test new API endpoint.\"\"\"
+    response = client.get('/new')
+    assert response.status_code == 200
+    assert 'data' in response.json()
+
 def test_old_function():
-    assert 1 == 1
+    # Updated implementation
+    assert 1 == 1
+    assert 2 == 2
"""

    result = analyze_pr_diff(diff_text)

    assert len(result.new_tests) == 1
    assert result.new_tests[0].test_name == "test_new_endpoint"
    assert len(result.updated_tests) == 1
    assert result.updated_tests[0].test_name == "test_old_function"


def test_analyze_new_file() -> None:
    """Test detection of tests in completely new file."""
    diff_text = """diff --git a/tests/test_new_module.py b/tests/test_new_module.py
new file mode 100644
index 0000000..abcdefg
--- /dev/null
+++ b/tests/test_new_module.py
@@ -0,0 +1,15 @@
+import pytest
+
+
+def test_first():
+    assert 1 == 1
+
+
+def test_second():
+    assert 2 == 2
+
+
+@pytest.mark.slow
+def test_third():
+    assert 3 == 3
"""

    result = analyze_pr_diff(diff_text)

    assert len(result.new_tests) == 3
    assert len(result.updated_tests) == 0

    test_names = [t.test_name for t in result.new_tests]
    assert "test_first" in test_names
    assert "test_second" in test_names
    assert "test_third" in test_names


def test_analyze_non_test_file_ignored() -> None:
    """Test that non-test files are ignored."""
    diff_text = """diff --git a/src/module.py b/src/module.py
index 1234567..abcdefg 100644
--- a/src/module.py
+++ b/src/module.py
@@ -10,6 +10,10 @@ def existing_function():
     return 1

+def test_function():
+    # This is not in a test file
+    return 2
+
"""

    result = analyze_pr_diff(diff_text)

    assert len(result.new_tests) == 0
    assert len(result.updated_tests) == 0


def test_analyze_empty_diff() -> None:
    """Test handling of empty diff."""
    result = analyze_pr_diff("")

    assert len(result.new_tests) == 0
    assert len(result.updated_tests) == 0


def test_analyze_multiple_files() -> None:
    """Test analysis of diff with multiple test files."""
    diff_text = """diff --git a/tests/test_api.py b/tests/test_api.py
index 1234567..abcdefg 100644
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -10,6 +10,10 @@ def test_existing():
     assert response.status_code == 200

+def test_api_new():
+    assert True
+
diff --git a/tests/test_models.py b/tests/test_models.py
index 1234567..abcdefg 100644
--- a/tests/test_models.py
+++ b/tests/test_models.py
@@ -10,6 +10,10 @@ def test_model():
     assert True

+def test_model_new():
+    assert True
+
"""

    result = analyze_pr_diff(diff_text)

    assert len(result.new_tests) == 2
    assert len(result.updated_tests) == 0

    filenames = [t.filename for t in result.new_tests]
    assert "tests/test_api.py" in filenames
    assert "tests/test_models.py" in filenames


def test_pytest_metrics_properties() -> None:
    """Test PytestMetrics model properties."""
    metrics = PytestMetrics(
        new_tests=[
            PytestInfo(filename="tests/test_a.py", test_name="test_one"),
            PytestInfo(filename="tests/test_b.py", test_name="test_two"),
        ],
        updated_tests=[PytestInfo(filename="tests/test_c.py", test_name="test_three")],
    )

    assert metrics.total_new == 2
    assert metrics.total_updated == 1


def test_pytest_info_model() -> None:
    """Test PytestInfo model."""
    test_info = PytestInfo(filename="tests/test_sample.py", test_name="test_example")

    assert test_info.filename == "tests/test_sample.py"
    assert test_info.test_name == "test_example"
