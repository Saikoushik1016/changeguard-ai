from changeguard_ai.models import PRMetadata
from changeguard_ai.services.iac_analyzer import analyze_iac


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


def test_no_iac_files():
    pr = make_pr(files_changed=["src/app.py", "src/auth.py"])
    result = analyze_iac(pr)
    assert result["has_iac_changes"] is False
    assert result["severity"] == "low"


def test_detects_iac_files():
    pr = make_pr(files_changed=["terraform/main.tf", "src/app.py"])
    result = analyze_iac(pr)
    assert result["has_iac_changes"] is True


def test_detects_secret_changes():
    pr = make_pr(files_changed=["terraform/secrets.tf"])
    result = analyze_iac(pr)
    assert result["has_secret_changes"] is True
    assert result["severity"] == "critical"


def test_detects_permission_changes():
    pr = make_pr(files_changed=["terraform/iam_role.tf"])
    result = analyze_iac(pr)
    assert result["has_permission_changes"] is True
    assert result["severity"] == "critical"


def test_detects_network_changes():
    pr = make_pr(files_changed=["k8s/ingress.yaml"])
    result = analyze_iac(pr)
    assert result["has_network_changes"] is True
    assert result["severity"] == "high"


def test_detects_database_changes():
    pr = make_pr(files_changed=["terraform/database.tf"])
    result = analyze_iac(pr)
    assert result["has_database_changes"] is True
    assert result["severity"] == "high"