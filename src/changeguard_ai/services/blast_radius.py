from changeguard_ai.models import PRMetadata

SHARED_CODE_FOLDERS = ["shared", "common", "utils", "lib", "core", "base"]
CRITICAL_PATH_SERVICES = ["api-gateway", "auth-service", "payment-service", "billing-service"]
DEPENDENCY_FILES = ["requirements.txt", "package.json", "go.mod", "Pipfile", "pyproject.toml"]


def get_affected_services(files: list[str]) -> list[str]:
    services = set()
    for f in files:
        parts = f.split("/")
        if len(parts) > 1:
            services.add(parts[0])
    return list(services)


def analyze_blast_radius(pr: PRMetadata) -> dict:
    files = pr.files_changed

    affected_services = get_affected_services(files)
    services_count = len(affected_services)

    touches_shared_code = any(
        folder in f.lower()
        for f in files
        for folder in SHARED_CODE_FOLDERS
    )

    touches_critical_path = any(
    service in f.lower()
    for f in files
    for service in CRITICAL_PATH_SERVICES
)

    touches_dependencies = any(
        f.endswith(dep) or dep in f
        for f in files
        for dep in DEPENDENCY_FILES
    )

    risk_signals = []

    if touches_shared_code:
        risk_signals.append("Shared or common code modified — affects multiple services")
    if touches_critical_path:
        risk_signals.append("Critical path service touched — auth, payment, or gateway")
    if touches_dependencies:
        risk_signals.append("Dependency files changed — affects entire application")
    if services_count > 3:
        risk_signals.append(f"Changes span {services_count} services — high blast radius")

    if touches_critical_path or touches_dependencies:
        estimated_impact = "critical"
    elif touches_shared_code or services_count > 3:
        estimated_impact = "high"
    elif services_count > 1:
        estimated_impact = "medium"
    else:
        estimated_impact = "low"

    return {
        "affected_services": affected_services,
        "services_count": services_count,
        "touches_shared_code": touches_shared_code,
        "touches_critical_path": touches_critical_path,
        "touches_dependencies": touches_dependencies,
        "estimated_user_impact": estimated_impact,
        "risk_signals": risk_signals,
    }