from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}