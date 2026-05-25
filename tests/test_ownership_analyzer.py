from changeguard_ai.models import PRMetadata
from changeguard_ai.services.ownership_analyzer import analyze_ownership


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


def test_single_team_low_severity():
    pr = make_pr(files_changed=["auth/login.py", "auth/logout.py"])
    result = analyze_ownership(pr)
    assert result["teams_count"] == 1
    assert result["is_cross_team"] is False
    assert result["severity"] == "low"


def test_cross_team_medium_severity():
    pr = make_pr(files_changed=["auth/login.py", "frontend/home.py"])
    result = analyze_ownership(pr)
    assert result["is_cross_team"] is True
    assert result["severity"] == "medium"


def test_tier1_service_high_severity():
    pr = make_pr(files_changed=["payment-service/invoice.py"])
    result = analyze_ownership(pr)
    assert result["has_tier1_service"] is True
    assert result["severity"] == "high"


def test_cross_team_tier1_critical():
    pr = make_pr(files_changed=["payment-service/invoice.py", "frontend/checkout.py"])
    result = analyze_ownership(pr)
    assert result["is_cross_team"] is True
    assert result["has_tier1_service"] is True
    assert result["severity"] == "critical"


def test_unknown_owner_flagged():
    pr = make_pr(files_changed=["random/unknown_file.py"])
    result = analyze_ownership(pr)
    assert len(result["unknown_owner_files"]) > 0