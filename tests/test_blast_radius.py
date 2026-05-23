from changeguard_ai.models import PRMetadata
from changeguard_ai.services.blast_radius import analyze_blast_radius


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


def test_single_service_low_impact():
    pr = make_pr(files_changed=["auth/login.py", "auth/logout.py"])
    result = analyze_blast_radius(pr)
    assert result["services_count"] == 1
    assert result["estimated_user_impact"] == "low"


def test_multiple_services_medium_impact():
    pr = make_pr(files_changed=["auth/login.py", "payment/invoice.py"])
    result = analyze_blast_radius(pr)
    assert result["services_count"] == 2
    assert result["estimated_user_impact"] == "medium"


def test_detects_shared_code():
    pr = make_pr(files_changed=["shared/utils.py", "auth/login.py"])
    result = analyze_blast_radius(pr)
    assert result["touches_shared_code"] is True
    assert result["estimated_user_impact"] == "high"


def test_detects_critical_path():
    pr = make_pr(files_changed=["auth-service/middleware.py"])
    result = analyze_blast_radius(pr)
    assert result["touches_critical_path"] is True
    assert result["estimated_user_impact"] == "critical"

def test_detects_dependency_changes():
    pr = make_pr(files_changed=["requirements.txt", "src/app.py"])
    result = analyze_blast_radius(pr)
    assert result["touches_dependencies"] is True
    assert result["estimated_user_impact"] == "critical"


def test_many_services_high_impact():
    pr = make_pr(files_changed=[
        "auth/login.py",
        "payment/invoice.py",
        "orders/create.py",
        "notifications/email.py",
    ])
    result = analyze_blast_radius(pr)
    assert result["services_count"] == 4
    assert result["estimated_user_impact"] == "high"