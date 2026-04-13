from fastapi import FastAPI

from changeguard_ai.api.health import router as health_router
from changeguard_ai.api.webhooks import router as webhook_router
from changeguard_ai.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ChangeGuard AI is running"}


app.include_router(health_router)
app.include_router(webhook_router)