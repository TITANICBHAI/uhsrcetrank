from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
app.include_router(public_router, prefix="/api")
app.include_router(admin_router, prefix="/admin")