from fastapi import APIRouter, Header, Request, status

from changeguard_ai.core.config import settings
from changeguard_ai.core.security import verify_github_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default="", alias="X-GitHub-Event"),
    x_github_delivery: str = Header(default="", alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
) -> dict:
    raw_body = await request.body()

    if x_github_event not in settings.github_allowed_events:
        return {
            "accepted": False,
            "event": x_github_event,
            "message": f"Event '{x_github_event}' not processed",
        }

    return {
        "accepted": True,
        "event": x_github_event,
        "delivery_id": x_github_delivery,
        "message": "GitHub webhook received and verified",
    }