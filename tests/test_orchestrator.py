from changeguard_ai.models import PRMetadata, RiskReport, RiskLevel
from changeguard_ai.services.orchestrator import run_orchestrator


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


def test_returns_risk_report():
    pr = make_pr()
    result = run_orchestrator(pr)
    assert isinstance(result, RiskReport)


def test_risk_score_in_valid_range():
    pr = make_pr()
    result = run_orchestrator(pr)
    assert 0 <= result.risk_score <= 100


def test_low_risk_pr():
    pr = make_pr(
        files_changed=["src/app.py"],
        additions=10,
        deletions=5,
    )
    result = run_orchestrator(pr)
    assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
    assert result.requires_human_review is False


def test_high_risk_pr():
    pr = make_pr(
        head_branch="hotfix/critical-bug",
        files_changed=[
            "terraform/secrets.tf",
            "shared/utils.py",
            "rollback/migration.py",
        ],
        additions=400,
        deletions=200,
    )
    result = run_orchestrator(pr)
    assert result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
    assert result.requires_human_review is True


def test_has_top_risk_factors():
    pr = make_pr(
        files_changed=["terraform/secrets.tf"],
    )
    result = run_orchestrator(pr)
    assert len(result.top_risk_factors) > 0


def test_has_rollout_recommendation():
    pr = make_pr()
    result = run_orchestrator(pr)
    assert result.recommended_rollout != ""
    assert len(result.recommended_rollout) > 0