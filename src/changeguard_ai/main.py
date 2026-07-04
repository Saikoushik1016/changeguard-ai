import logging
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from changeguard_ai.api.health import router as health_router
from changeguard_ai.api.webhooks import router as webhook_router
from changeguard_ai.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("changeguard")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_completed", extra={"request_id": request_id, "path": request.url.path})
        return response


app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(RequestIDMiddleware)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ChangeGuard AI is running"}


app.include_router(health_router)
app.include_router(webhook_router)