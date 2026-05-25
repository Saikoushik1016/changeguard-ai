from changeguard_ai.models import PRMetadata

HOTFIX_PATTERNS = ["hotfix/", "hot-fix/", "hotfix_", "hot_fix_"]
ROLLBACK_PATTERNS = ["rollback/", "revert/", "roll-back/"]
INCIDENT_PATTERNS = ["incident/", "postmortem/", "post-mortem/"]
RISKY_BRANCH_PREFIXES = ["hotfix/", "emergency/", "quick-fix/", "urgent/", "patch/"]
CHANGELOG_FILES = ["CHANGELOG.md", "CHANGELOG.txt", "version.py", "VERSION"]


def check_file_patterns(files: list[str], patterns: list[str]) -> bool:
    return any(
        pattern in f.lower()
        for f in files
        for pattern in patterns
    )


def is_risky_branch(branch_name: str) -> bool:
    branch_lower = branch_name.lower()
    return any(branch_lower.startswith(prefix) for prefix in RISKY_BRANCH_PREFIXES)


def analyze_history(pr: PRMetadata) -> dict:
    files = pr.files_changed

    has_hotfix_patterns = check_file_patterns(files, HOTFIX_PATTERNS)
    has_rollback_patterns = check_file_patterns(files, ROLLBACK_PATTERNS)
    has_incident_patterns = check_file_patterns(files, INCIDENT_PATTERNS)
    risky_branch_name = is_risky_branch(pr.head_branch)

    touches_changelog = any(
        any(f.endswith(cf) or cf in f for cf in CHANGELOG_FILES)
        for f in files
    )

    risk_signals = []

    if has_hotfix_patterns:
        risk_signals.append("Hotfix patterns detected in file paths — suggests past instability")
    if has_rollback_patterns:
        risk_signals.append("Rollback or revert patterns found — this area has been unstable")
    if has_incident_patterns:
        risk_signals.append("Incident or postmortem files touched — review history carefully")
    if risky_branch_name:
        risk_signals.append(f"Branch name '{pr.head_branch}' suggests urgency — slow down and review")
    if touches_changelog:
        risk_signals.append("Changelog or version file modified alongside code changes")

    critical_signals = sum([
        has_hotfix_patterns,
        has_rollback_patterns,
        has_incident_patterns,
        risky_branch_name,
    ])

    if critical_signals >= 2:
        severity = "critical"
    elif critical_signals == 1:
        severity = "high"
    elif touches_changelog:
        severity = "medium"
    else:
        severity = "low"

    return {
        "has_hotfix_patterns": has_hotfix_patterns,
        "has_rollback_patterns": has_rollback_patterns,
        "has_incident_patterns": has_incident_patterns,
        "risky_branch_name": risky_branch_name,
        "touches_changelog": touches_changelog,
        "risk_signals": risk_signals,
        "severity": severity,
    }