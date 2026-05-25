from changeguard_ai.models import PRMetadata
from changeguard_ai.services.history_analyzer import analyze_history


def make_pr(**kwargs) -> PRMetadata:
    defaults = {
        "pr_number": 1,
        "title": "Test PR",
        "author": "testuser",
        "base_branch": "main",
        "head_branch": "feat/normal-feature",
        "repo_full_name": "org/repo",
        "additions": 10,
        "deletions": 5,
        "pr_url": "https://github.com/org/repo/pull/1",
        "files_changed": ["src/app.py"],
    }
    defaults.update(kwargs)
    return PRMetadata(**defaults)


def test_clean_pr_low_severity():
    pr = make_pr()
    result = analyze_history(pr)
    assert result["severity"] == "low"
    assert len(result["risk_signals"]) == 0


def test_detects_hotfix_in_file_path():
    pr = make_pr(files_changed=["hotfix/auth_bug.py"])
    result = analyze_history(pr)
    assert result["has_hotfix_patterns"] is True
    assert result["severity"] == "high"


def test_detects_rollback_in_file_path():
    pr = make_pr(files_changed=["rollback/migration_v2.py"])
    result = analyze_history(pr)
    assert result["has_rollback_patterns"] is True
    assert result["severity"] == "high"


def test_detects_risky_branch_name():
    pr = make_pr(head_branch="hotfix/payment-crash")
    result = analyze_history(pr)
    assert result["risky_branch_name"] is True
    assert result["severity"] == "high"


def test_multiple_signals_critical():
    pr = make_pr(
        head_branch="hotfix/auth-crash",
        files_changed=["rollback/migration.py"]
    )
    result = analyze_history(pr)
    assert result["severity"] == "critical"


def test_detects_changelog():
    pr = make_pr(files_changed=["CHANGELOG.md", "src/app.py"])
    result = analyze_history(pr)
    assert result["touches_changelog"] is True
    assert result["severity"] == "medium"