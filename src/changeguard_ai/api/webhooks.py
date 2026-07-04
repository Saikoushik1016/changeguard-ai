import json
import logging
import traceback

from fastapi import APIRouter, Header, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse

from changeguard_ai.core.config import settings
from changeguard_ai.core.security import verify_github_signature
from changeguard_ai.models import PRMetadata
from changeguard_ai.services.orchestrator import run_orchestrator
from changeguard_ai.services.github_client import fetch_pr_files, post_pr_comment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

processing_deliveries: set[str] = set()


async def process_pull_request(
    payload: dict,
    repo: str,
    pr_number: int,
    delivery_id: str | None = None,
) -> None:
    print(f"[ChangeGuard] Starting analysis for PR #{pr_number} in {repo}")

    try:
        pr_data = payload["pull_request"]
        print(f"[ChangeGuard] Fetching changed files from GitHub API...")

        files_changed = await fetch_pr_files(repo, pr_number)
        print(f"[ChangeGuard] Got {len(files_changed)} files: {files_changed}")

        pr = PRMetadata(
            pr_number=pr_number,
            title=pr_data["title"],
            author=pr_data["user"]["login"],
            base_branch=pr_data["base"]["ref"],
            head_branch=pr_data["head"]["ref"],
            repo_full_name=repo,
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            pr_url=pr_data["html_url"],
            files_changed=files_changed,
        )

        print(f"[ChangeGuard] Running orchestrator...")
        report = run_orchestrator(pr)
        print(f"[ChangeGuard] Risk score: {report.risk_score}/100 ({report.risk_level.value})")

        print(f"[ChangeGuard] Posting comment to PR...")
        success = await post_pr_comment(repo, pr_number, report)

        if success:
            print(f"[ChangeGuard] Comment posted successfully to PR #{pr_number}")
        else:
            print(f"[ChangeGuard] Failed to post comment — check GITHUB_TOKEN")

    except KeyError as e:
        print(f"[ChangeGuard] KeyError in payload: {e}")
        print(traceback.format_exc())
    except Exception as e:
        print(f"[ChangeGuard] Error processing PR #{pr_number}: {e}")
        print(traceback.format_exc())
    finally:
        if delivery_id:
            processing_deliveries.discard(delivery_id)


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

    print(f"[ChangeGuard] Received event: {x_github_event}")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid JSON payload"},
        )

    if x_github_event not in settings.github_allowed_events:
        print(f"[ChangeGuard] Ignoring event: {x_github_event}")
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "accepted": False,
                "event": x_github_event,
                "message": f"Event '{x_github_event}' not processed",
            },
        )

    delivery_id = x_github_delivery or ""
    if delivery_id:
        if delivery_id in processing_deliveries:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "accepted": False,
                    "event": x_github_event,
                    "delivery_id": delivery_id,
                    "message": "Duplicate delivery ignored",
                },
            )
        processing_deliveries.add(delivery_id)

    action = payload.get("action", "")
    print(f"[ChangeGuard] Event: {x_github_event}, Action: {action}")

    should_queue = False
    if x_github_event == "pull_request":
        if action in ("opened", "synchronize", "reopened"):
            repo = payload["repository"]["full_name"]
            pr_number = payload["number"]
            print(f"[ChangeGuard] Queuing analysis for PR #{pr_number} in {repo}")
            background_tasks.add_task(
                process_pull_request,
                payload,
                repo,
                pr_number,
                delivery_id or None,
            )
            should_queue = True
        else:
            print(f"[ChangeGuard] Ignoring pull_request action: {action}")

    if not should_queue and delivery_id:
        processing_deliveries.discard(delivery_id)

    return {
        "accepted": True,
        "event": x_github_event,
        "delivery_id": x_github_delivery,
        "message": "Webhook received and queued for processing",
    }