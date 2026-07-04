import asyncio

from changeguard_ai.models import RiskLevel, RiskReport
from changeguard_ai.services import github_client


class DummyResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class DummyAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def make_report() -> RiskReport:
    return RiskReport(
        pr_number=1,
        repo="octo/repo",
        risk_score=42,
        risk_level=RiskLevel.MEDIUM,
        summary="Test summary",
        top_risk_factors=["Test factor"],
        recommended_rollout="standard deploy",
        requires_human_review=False,
    )


def test_get_headers_include_user_agent():
    headers = github_client.get_headers()

    assert headers["User-Agent"] == "changeguard-ai"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"


def test_post_pr_comment_returns_false_on_forbidden(monkeypatch, caplog):
    class ForbiddenClient(DummyAsyncClient):
        async def post(self, *args, **kwargs):
            return DummyResponse(403, '{"message":"Resource not accessible by integration"}')

    monkeypatch.setattr(github_client.httpx, "AsyncClient", lambda *args, **kwargs: ForbiddenClient(None))
    monkeypatch.setattr(github_client.settings, "github_token", "fake-token")

    result = asyncio.run(github_client.post_pr_comment("octo/repo", 7, make_report()))

    assert result is False
    assert "GitHub API rejected comment request" in caplog.text
