from changeguard_ai.models import PRMetadata

TEAM_OWNERSHIP = {
    "auth": "team-security",
    "payment": "team-payments",
    "billing": "team-payments",
    "api": "team-platform",
    "gateway": "team-platform",
    "frontend": "team-frontend",
    "ui": "team-frontend",
    "database": "team-data",
    "migrations": "team-data",
    "infra": "team-devops",
    "terraform": "team-devops",
    "k8s": "team-devops",
    "helm": "team-devops",
}

TIER1_SERVICES = [
    "payment-service", "billing-service",
    "api-gateway", "checkout-service", "order-service"
]


def infer_owner(filepath: str) -> str:
    filepath_lower = filepath.lower()
    for folder, team in TEAM_OWNERSHIP.items():
        if folder in filepath_lower:
            return team
    return "team-unknown"


def analyze_ownership(pr: PRMetadata) -> dict:
    files = pr.files_changed

    owners = list({infer_owner(f) for f in files})
    teams_count = len(owners)

    is_cross_team = teams_count > 1

    has_tier1_service = any(
        service in f.lower()
        for f in files
        for service in TIER1_SERVICES
    )

    unknown_owners = [
        f for f in files
        if infer_owner(f) == "team-unknown"
    ]

    risk_signals = []

    if is_cross_team:
        risk_signals.append(
            f"Cross-team change — {teams_count} teams affected: {', '.join(owners)}"
        )
    if has_tier1_service:
        risk_signals.append("Tier-1 service touched — requires senior review")
    if unknown_owners:
        risk_signals.append(
            f"{len(unknown_owners)} files have no clear owner"
        )

    if has_tier1_service and is_cross_team:
        severity = "critical"
    elif has_tier1_service or teams_count > 2:
        severity = "high"
    elif is_cross_team:
        severity = "medium"
    else:
        severity = "low"

    return {
        "owners": owners,
        "teams_count": teams_count,
        "is_cross_team": is_cross_team,
        "has_tier1_service": has_tier1_service,
        "unknown_owner_files": unknown_owners,
        "risk_signals": risk_signals,
        "severity": severity,
    }