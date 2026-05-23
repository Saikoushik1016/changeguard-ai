import pytest
from changeguard_ai.models import PRMetadata
from changeguard_ai.services.diff_analyzer import analyze_diff


def make_pr(**kwargs) -> PRMetadata:
    defaults = {
        "pr_number": 1,
        "title": "Test PR",
        "author": "testuser",
        "base_branch": "main",
        "head_branch": "feat/test",
        "repo_full_name": "org/repo",
        "additions": 10,
        "deletions": 5,
        "pr_url": "https://github.com/org/repo/pull/1",
        "files_changed": ["src/app.py"],
    }
    defaults.update(kwargs)
    return PRMetadata(**defaults)


def test_low_churn():
    pr = make_pr(additions=10, deletions=5)
    result = analyze_diff(pr)
    assert result["churn_score"] < 0.1


def test_detects_migration():
    pr = make_pr(files_changed=["src/app.py", "migrations/0012_add_users.py"])
    result = analyze_diff(pr)
    assert result["has_migration"] is True


def test_detects_config_changes():
    pr = make_pr(files_changed=["src/app.py", "deploy/values.yaml"])
    result = analyze_diff(pr)
    assert result["has_config_changes"] is True


def test_high_churn():
    pr = make_pr(additions=400, deletions=200)
    result = analyze_diff(pr)