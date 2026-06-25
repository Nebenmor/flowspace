from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.workspaces import router as workspace_router
from app.api.v1.invitations import router as invitation_router
from app.api.v1.tasks import router as task_router
from app.api.v1.labels import router as label_router
from app.api.v1.custom_fields import router as custom_field_router
from app.api.v1.activities import router as activity_router
from app.api.v1.websockets import router as ws_router
from app.api.v1.notifications import router as notification_router
from app.api.v1.webhooks import router as webhook_router
from app.api.v1.analytics import router as analytics_router
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RateLimitMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# Middleware — registered before routers
app.add_middleware(RateLimitMiddleware)

register_exception_handlers(app)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(invitation_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(label_router, prefix="/api/v1")
app.include_router(custom_field_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")
app.include_router(ws_router)
app.include_router(notification_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        print("✅ Database connection established")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}