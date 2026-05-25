import logging
from fastapi import APIRouter, Header, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse

from changeguard_ai.core.config import settings
from changeguard_ai.core.security import verify_github_signature
from changeguard_ai.models import PRMetadata
from changeguard_ai.services.orchestrator import run_orchestrator
from changeguard_ai.services.github_client import fetch_pr_files, post_pr_comment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def process_pull_request(payload: dict, repo: str, pr_number: int):
    try:
        pr_data = payload["pull_request"]

        files_changed = await fetch_pr_files(repo, pr_number)

        pr = PRMetadata(
            pr_number=pr_number,
            title=pr_data["title"],
            author=pr_data["user"]["login"],
            base_branch=pr_data["base"]["ref"],
            head_branch=pr_data["head"]["ref"],
            repo_full_name=repo,
            additions=pr_data["additions"],
            deletions=pr_data["deletions"],
            pr_url=pr_data["html_url"],
            files_changed=files_changed,
        )

        report = run_orchestrator(pr)

        await post_pr_comment(repo, pr_number, report)

        logger.info(
            f"PR #{pr_number} in {repo} scored {report.risk_score}/100 "
            f"({report.risk_level.value})"
        )

    except Exception as e:
        logger.error(f"Failed to process PR #{pr_number} in {repo}: {e}")


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    x_github_delivery: str = Header(default="", alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
) -> dict:
    raw_body = await request.body()

    verify_github_signature(
        payload_body=raw_body,
        secret_token=settings.github_webhook_secret,
        signature_header=x_hub_signature_256,
    )

    if x_github_event not in settings.github_allowed_events:
        return JSONResponse({
            "accepted": False,
            "event": x_github_event,
            "message": f"Event '{x_github_event}' not processed",
        })

    import json
    payload = json.loads(raw_body)

    if x_github_event == "pull_request":
        action = payload.get("action", "")
        if action in ("opened", "synchronize", "reopened"):
            repo = payload["repository"]["full_name"]
            pr_number = payload["number"]
            background_tasks.add_task(
                process_pull_request, payload, repo, pr_number
            )
            logger.info(f"Queued analysis for PR #{pr_number} in {repo}")

    return {
        "accepted": True,
        "event": x_github_event,
        "delivery_id": x_github_delivery,
        "message": "Webhook received and queued for processing",
    }