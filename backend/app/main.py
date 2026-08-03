from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import marketlens_error_handler
from app.api.routes.analyses import router as analyses_router
from app.api.routes.companies import router as companies_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import MarketLensError
from app.db.session import init_database

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Educational analysis of official Indian market announcements.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)
app.add_exception_handler(MarketLensError, marketlens_error_handler)


@app.middleware("http")
async def add_request_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a correlation ID without logging request bodies."""
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router, prefix="/api")
app.include_router(analyses_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
