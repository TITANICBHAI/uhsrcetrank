from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import create_tables
from app.routers.admin import router as admin_router
from app.routers.public import router as public_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="UHSR CET Rank Calculator API",
    description="Independent candidate utility API. Not an official UHSR service.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Secret"],
)


@app.middleware("http")
async def admin_no_store(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/admin/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(public_router, prefix="/api")
app.include_router(admin_router, prefix="/admin")

frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")