import json

import pytest
from fastapi.testclient import TestClient

from changeguard_ai.api import webhooks
from changeguard_ai.main import app


@pytest.fixture(autouse=True)
def clear_delivery_state():
    webhooks.processing_deliveries.clear()
    yield
    webhooks.processing_deliveries.clear()


client = TestClient(app)


def make_payload(action: str = "opened") -> dict:
    return {
        "action": action,
        "number": 7,
        "repository": {"full_name": "octo/repo"},
        "pull_request": {
            "title": "Add feature",
            "user": {"login": "octocat"},
            "base": {"ref": "main"},
            "head": {"ref": "feature/test"},
            "html_url": "https://github.com/octo/repo/pull/7",
            "additions": 10,
            "deletions": 5,
        },
    }


def test_invalid_signature_returns_forbidden():
    response = client.post(
        "/webhooks/github",
        content="{}",
        headers={"X-GitHub-Event": "pull_request"},
    )

    assert response.status_code == 403


def test_malformed_json_returns_bad_request(monkeypatch):
    monkeypatch.setattr(webhooks, "verify_github_signature", lambda **kwargs: None)

    response = client.post(
        "/webhooks/github",
        content="{not-json",
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=test",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON payload"


def test_duplicate_delivery_is_ignored(monkeypatch):
    monkeypatch.setattr(webhooks, "verify_github_signature", lambda **kwargs: None)

    calls = []

    async def fake_process(payload, repo, pr_number, delivery_id=None):
        calls.append((payload["number"], repo, pr_number, delivery_id))

    monkeypatch.setattr(webhooks, "process_pull_request", fake_process)

    payload = json.dumps(make_payload())
    headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "delivery-123",
        "X-Hub-Signature-256": "sha256=test",
    }

    first_response = client.post("/webhooks/github", content=payload, headers=headers)
    second_response = client.post("/webhooks/github", content=payload, headers=headers)

    assert first_response.status_code == 202
    assert second_response.status_code == 409
    assert len(calls) == 1
