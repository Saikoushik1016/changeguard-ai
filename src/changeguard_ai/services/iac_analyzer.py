from changeguard_ai.models import PRMetadata

IAC_EXTENSIONS = {".tf", ".hcl", ".yaml", ".yml"}
IAC_FOLDERS = ["terraform", "helm", "k8s", "kubernetes", "charts", "infra", "infrastructure"]

SECRET_PATTERNS = ["secret", "credential", "password", "token", "key", "cert"]
PERMISSION_PATTERNS = ["iam", "role", "policy", "permission", "access", "rbac"]
NETWORK_PATTERNS = ["ingress", "egress", "security_group", "firewall", "vpc", "network"]
DATABASE_PATTERNS = ["database", "rds", "postgres", "mysql", "mongo", "redis"]
AUTOSCALING_PATTERNS = ["autoscaling", "replicas", "min_count", "max_count", "desired_count"]


def is_iac_file(filepath: str) -> bool:
    filepath_lower = filepath.lower()
    has_iac_extension = any(filepath_lower.endswith(ext) for ext in IAC_EXTENSIONS)
    in_iac_folder = any(folder in filepath_lower for folder in IAC_FOLDERS)
    return has_iac_extension and in_iac_folder


def check_patterns(files: list[str], patterns: list[str]) -> bool:
    return any(
        pattern in f.lower()
        for f in files
        for pattern in patterns
    )


def analyze_iac(pr: PRMetadata) -> dict:
    files = pr.files_changed

    iac_files = [f for f in files if is_iac_file(f)]

    if not iac_files:
        return {
            "has_iac_changes": False,
            "iac_files": [],
            "has_secret_changes": False,
            "has_permission_changes": False,
            "has_network_changes": False,
            "has_database_changes": False,
            "risk_signals": [],
            "severity": "low",
        }

    has_secret_changes = check_patterns(iac_files, SECRET_PATTERNS)
    has_permission_changes = check_patterns(iac_files, PERMISSION_PATTERNS)
    has_network_changes = check_patterns(iac_files, NETWORK_PATTERNS)
    has_database_changes = check_patterns(iac_files, DATABASE_PATTERNS)

    risk_signals = []

    if has_secret_changes:
        risk_signals.append("Secret or credential files modified in IaC")
    if has_permission_changes:
        risk_signals.append("IAM or permission configuration changed")
    if has_network_changes:
        risk_signals.append("Network or firewall rules modified")
    if has_database_changes:
        risk_signals.append("Database configuration changed")
    if len(iac_files) > 3:
        risk_signals.append(f"{len(iac_files)} infrastructure files changed in one PR")

    if has_secret_changes or has_permission_changes:
        severity = "critical"
    elif has_network_changes or has_database_changes:
        severity = "high"
    elif iac_files:
        severity = "medium"
    else:
        severity = "low"

    return {
        "has_iac_changes": True,
        "iac_files": iac_files,
        "has_secret_changes": has_secret_changes,
        "has_permission_changes": has_permission_changes,
        "has_network_changes": has_network_changes,
        "has_database_changes": has_database_changes,
        "risk_signals": risk_signals,
        "severity": severity,
    }