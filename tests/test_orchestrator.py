from changeguard_ai.models import PRMetadata, RiskReport, RiskLevel
from changeguard_ai.services.orchestrator import build_risk_decision, run_orchestrator


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


def test_build_risk_decision_marks_safe_changes_as_low_risk():
    pr = make_pr(files_changed=["src/app.py"], additions=10, deletions=5)
    signals = {
        "diff": {"churn_score": 0.02, "has_migration": False, "test_ratio": 0.5, "risk_signals": []},
        "iac": {"has_iac_changes": False, "has_secret_changes": False, "has_permission_changes": False, "severity": "low", "risk_signals": []},
        "blast": {"services_count": 1, "touches_shared_code": False, "touches_critical_path": False, "estimated_user_impact": "low", "risk_signals": []},
        "ownership": {"teams_count": 1, "is_cross_team": False, "has_tier1_service": False, "severity": "low", "risk_signals": []},
        "history": {"has_hotfix_patterns": False, "has_rollback_patterns": False, "risky_branch_name": False, "severity": "low", "risk_signals": []},
    }

    decision = build_risk_decision(pr, signals)

    assert decision["risk_level"] == "low"
    assert decision["risk_score"] <= 25
    assert decision["requires_human_review"] is False


def test_build_risk_decision_flags_critical_signals():
    pr = make_pr(
        head_branch="hotfix/critical-bug",
        files_changed=["terraform/secrets.tf", "shared/utils.py", "rollback/migration.py"],
        additions=400,
        deletions=200,
    )
    signals = {
        "diff": {"churn_score": 0.9, "has_migration": True, "test_ratio": 0.0, "risk_signals": ["Large change", "Database migration detected"]},
        "iac": {"has_iac_changes": True, "has_secret_changes": True, "has_permission_changes": True, "severity": "critical", "risk_signals": ["Secret or credential files modified in IaC"]},
        "blast": {"services_count": 3, "touches_shared_code": True, "touches_critical_path": True, "estimated_user_impact": "critical", "risk_signals": ["Critical path service touched"]},
        "ownership": {"teams_count": 2, "is_cross_team": True, "has_tier1_service": True, "severity": "critical", "risk_signals": ["Cross-team change", "Tier-1 service touched"]},
        "history": {"has_hotfix_patterns": True, "has_rollback_patterns": True, "risky_branch_name": True, "severity": "critical", "risk_signals": ["Hotfix patterns detected", "Rollback or revert patterns found", "Branch name suggests urgency"]},
    }

    decision = build_risk_decision(pr, signals)

    assert decision["risk_level"] in {"high", "critical"}
    assert decision["risk_score"] >= 75
    assert decision["requires_human_review"] is True
    assert len(decision["top_risk_factors"]) > 0