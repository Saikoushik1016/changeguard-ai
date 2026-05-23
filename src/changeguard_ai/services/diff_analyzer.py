from changeguard_ai.models import PRMetadata


CONFIG_EXTENSIONS = {".yaml", ".yml", ".toml", ".json", ".env", ".tf", ".hcl"}
MIGRATION_PATTERNS = ["migration", "migrate", "schema", "alembic", "flyway"]
TEST_PATTERNS = ["test_", "_test.py", "spec.py"]


def analyze_diff(pr: PRMetadata) -> dict:
    files = pr.files_changed
    total_lines = pr.additions + pr.deletions

    churn_score = min(total_lines / 500, 1.0)

    has_migration = any(
        pattern in f.lower()
        for f in files
        for pattern in MIGRATION_PATTERNS
    )

    test_files = [f for f in files if any(p in f for p in TEST_PATTERNS)]
    test_ratio = len(test_files) / len(files) if files else 0.0

    has_config_changes = any(
        f.endswith(tuple(CONFIG_EXTENSIONS))
        for f in files
    )

    risk_signals = []
    if churn_score > 0.7:
        risk_signals.append(f"Large change: {total_lines} lines modified")
    if has_migration:
        risk_signals.append("Database migration detected")
    if test_ratio < 0.1 and len(files) > 3:
        risk_signals.append("Low test coverage in this PR")
    if has_config_changes:
        risk_signals.append("Config or infrastructure files changed")

    return {
        "churn_score": round(churn_score, 2),
        "has_migration": has_migration,
        "test_ratio": round(test_ratio, 2),
        "has_config_changes": has_config_changes,
        "risk_signals": risk_signals,
    }