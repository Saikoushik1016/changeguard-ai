import json
import os
from changeguard_ai.models import PRMetadata, RiskReport, RiskLevel
from changeguard_ai.services.diff_analyzer import analyze_diff
from changeguard_ai.services.iac_analyzer import analyze_iac
from changeguard_ai.services.blast_radius import analyze_blast_radius
from changeguard_ai.services.ownership_analyzer import analyze_ownership
from changeguard_ai.services.history_analyzer import analyze_history


def build_prompt(pr: PRMetadata, signals: dict) -> str:
    return f"""You are ChangeGuard AI, a deployment risk assessment system.
Analyze this pull request and return a risk assessment as JSON.

PR DETAILS:
- Title: {pr.title}
- Author: {pr.author}
- Repository: {pr.repo_full_name}
- Branch: {pr.head_branch} -> {pr.base_branch}
- Changes: {pr.additions + pr.deletions} lines across {len(pr.files_changed)} files

AGENT SIGNALS:
Diff Analysis:
- Churn score: {signals['diff']['churn_score']} (0=tiny, 1=massive)
- Database migration: {signals['diff']['has_migration']}
- Test ratio: {signals['diff']['test_ratio']}
- Risk signals: {signals['diff']['risk_signals']}

IaC Analysis:
- IaC changes found: {signals['iac']['has_iac_changes']}
- Secret changes: {signals['iac']['has_secret_changes']}
- Permission changes: {signals['iac']['has_permission_changes']}
- Severity: {signals['iac']['severity']}
- Risk signals: {signals['iac']['risk_signals']}

Blast Radius:
- Services affected: {signals['blast']['services_count']}
- Touches shared code: {signals['blast']['touches_shared_code']}
- Touches critical path: {signals['blast']['touches_critical_path']}
- Estimated impact: {signals['blast']['estimated_user_impact']}
- Risk signals: {signals['blast']['risk_signals']}

Ownership:
- Teams affected: {signals['ownership']['teams_count']}
- Cross team change: {signals['ownership']['is_cross_team']}
- Tier-1 service: {signals['ownership']['has_tier1_service']}
- Risk signals: {signals['ownership']['risk_signals']}

History:
- Hotfix patterns: {signals['history']['has_hotfix_patterns']}
- Rollback patterns: {signals['history']['has_rollback_patterns']}
- Risky branch name: {signals['history']['risky_branch_name']}
- Severity: {signals['history']['severity']}
- Risk signals: {signals['history']['risk_signals']}

Based on all signals above, return ONLY a JSON object with these exact fields:
{{
  "risk_score": <integer 0-100>,
  "risk_level": <"low"|"medium"|"high"|"critical">,
  "summary": "<2-3 sentence plain English summary>",
  "top_risk_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "recommended_rollout": "<e.g. canary at 5% or standard deploy>",
  "requires_human_review": <true|false>
}}

Respond with ONLY the JSON object. No explanation. No markdown.
"""


def get_mock_response(signals: dict) -> dict:
    severities = [
        signals['iac']['severity'],
        signals['blast']['estimated_user_impact'],
        signals['ownership']['severity'],
        signals['history']['severity'],
    ]

    if "critical" in severities:
        score = 85
        level = "critical"
        rollout = "do not deploy — requires senior review first"
        human_review = True
    elif "high" in severities:
        score = 65
        level = "high"
        rollout = "canary deploy at 5% with monitoring"
        human_review = True
    elif "medium" in severities:
        score = 40
        level = "medium"
        rollout = "standard deploy with extra monitoring"
        human_review = False
    else:
        score = 15
        level = "low"
        rollout = "standard deploy"
        human_review = False

    all_signals = (
        signals['diff']['risk_signals'] +
        signals['iac']['risk_signals'] +
        signals['blast']['risk_signals'] +
        signals['ownership']['risk_signals'] +
        signals['history']['risk_signals']
    )

    top_factors = all_signals[:3] if all_signals else ["No significant risk factors detected"]

    return {
        "risk_score": score,
        "risk_level": level,
        "summary": f"This PR has been assessed as {level} risk based on analysis across 5 dimensions.",
        "top_risk_factors": top_factors,
        "recommended_rollout": rollout,
        "requires_human_review": human_review,
    }


def call_claude(prompt: str) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        return json.loads(response_text)
    except Exception:
        return None


def run_orchestrator(pr: PRMetadata) -> RiskReport:
    signals = {
        "diff": analyze_diff(pr),
        "iac": analyze_iac(pr),
        "blast": analyze_blast_radius(pr),
        "ownership": analyze_ownership(pr),
        "history": analyze_history(pr),
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        prompt = build_prompt(pr, signals)
        result = call_claude(prompt)
    else:
        result = None

    if result is None:
        result = get_mock_response(signals)

    return RiskReport(
        pr_number=pr.pr_number,
        repo=pr.repo_full_name,
        risk_score=result["risk_score"],
        risk_level=RiskLevel(result["risk_level"]),
        summary=result["summary"],
        top_risk_factors=result["top_risk_factors"],
        recommended_rollout=result["recommended_rollout"],
        requires_human_review=result["requires_human_review"],
    )