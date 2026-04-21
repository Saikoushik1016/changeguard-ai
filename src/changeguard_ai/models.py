from pydantic import BaseModel, Field
from enum import Enum
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PRMetadata(BaseModel):
    pr_number: int
    title: str
    author: str
    base_branch: str
    head_branch: str
    repo_full_name: str
    additions: int
    deletions: int
    pr_url: str
    files_changed: list[str] = []


class RiskReport(BaseModel):
    pr_number: int
    repo: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    summary: str
    top_risk_factors: list[str]
    recommended_rollout: str
    requires_human_review: bool
