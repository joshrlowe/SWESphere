"""FastAPI application factory with production-ready configuration."""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.config import settings
from app.core.events import on_shutdown, on_startup

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup/shutdown events.

    Handles:
    - Database connection pool initialization
    - Redis connection setup
    - Background task scheduler startup
    - Graceful shutdown of all connections
    """
    logger.info(f"Starting {settings.APP_NAME} v{app.version}")
    await on_startup()
    yield
    await on_shutdown()
    logger.info(f"{settings.APP_NAME} shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
## SWESphere API

A modern, async-first social media platform API built with FastAPI.

### Features
- **Authentication**: JWT-based auth with access/refresh tokens
- **Users**: Profile management, follow/unfollow
- **Posts**: Create, like, reply, repost
- **Notifications**: Real-time notification system
- **Search**: Full-text search for users and posts

### Authentication
Most endpoints require a valid JWT token. Include it in the `Authorization` header:
```
Authorization: Bearer <your_access_token>
```

### Rate Limiting
API requests are rate-limited to prevent abuse:
- Anonymous: 30 requests/minute
- Authenticated: 60 requests/minute
        """,
        version="1.0.0",
        openapi_url=(
            f"{settings.API_V1_PREFIX}/openapi.json"
            if not settings.is_production
            else None
        ),
        docs_url=(
            f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else None
        ),
        redoc_url=(
            f"{settings.API_V1_PREFIX}/redoc" if not settings.is_production else None
        ),
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        # OpenAPI customization
        openapi_tags=[
            {
                "name": "Authentication",
                "description": "User authentication and token management",
            },
            {
                "name": "Users",
                "description": "User profile and social features",
            },
            {
                "name": "Posts",
                "description": "Post creation, interaction, and feeds",
            },
            {
                "name": "Comments",
                "description": "Comment management on posts",
            },
            {
                "name": "Notifications",
                "description": "User notification management",
            },
            {
                "name": "WebSocket",
                "description": "Real-time communication via WebSocket",
            },
            {
                "name": "Health",
                "description": "Health check and monitoring endpoints",
            },
        ],
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "persistAuthorization": True,
            "displayRequestDuration": True,
        },
    )

    # ===================
    # Middleware
    # ===================

    # CORS middleware - allow SvelteKit dev server and mobile apps
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # Request ID and timing middleware
    @app.middleware("http")
    async def add_request_metadata(request: Request, call_next):
        """Add request ID and process time headers."""
        request_id = str(uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # Log slow requests
        if process_time > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s [request_id={request_id}]"
            )

        return response

    # ===================
    # Exception Handlers
    # ===================

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> ORJSONResponse:
        """Handle HTTP exceptions with consistent format."""
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        """Handle validation errors with detailed field information."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "details": errors,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> ORJSONResponse:
        """Handle unexpected exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(f"Unhandled exception [request_id={request_id}]: {exc}")

        # Don't expose internal errors in production
        message = "Internal server error"
        if settings.DEBUG:
            message = str(exc)

        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": message,
                    "request_id": request_id,
                }
            },
        )

    # ===================
    # Routes
    # ===================

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Health check endpoints
    @app.get(
        "/health",
        tags=["Health"],
        summary="Basic health check",
        response_model=dict[str, Any],
    )
    async def health_check() -> dict[str, Any]:
        """
        Basic health check endpoint.

        Returns application status and version.
        """
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    @app.get(
        "/health/ready",
        tags=["Health"],
        summary="Readiness check",
        response_model=dict[str, Any],
    )
    async def readiness_check() -> dict[str, Any]:
        """
        Readiness check endpoint.

        Verifies database and Redis connectivity.
        """
        from app.db.session import engine
        from app.dependencies import get_redis

        checks: dict[str, Any] = {
            "status": "ready",
            "checks": {},
        }

        # Check database
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            checks["checks"]["database"] = "ok"
        except Exception as e:
            checks["status"] = "degraded"
            checks["checks"]["database"] = f"error: {str(e)}"

        # Check Redis
        try:
            redis = await get_redis()
            await redis.ping()
            checks["checks"]["redis"] = "ok"
        except Exception as e:
            checks["status"] = "degraded"
            checks["checks"]["redis"] = f"error: {str(e)}"

        return checks

    @app.get(
        "/health/live",
        tags=["Health"],
        summary="Liveness check",
    )
    async def liveness_check() -> dict[str, str]:
        """
        Liveness check endpoint.

        Simple check that the application is running.
        """
        return {"status": "alive"}

    return app


# Create application instance
app = create_app()
