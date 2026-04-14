from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.workspaces import router as workspace_router
from app.api.v1.invitations import router as invitation_router
from app.core.exceptions import register_exception_handlers

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

register_exception_handlers(app)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(invitation_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        print("✅ Database connection established")

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}