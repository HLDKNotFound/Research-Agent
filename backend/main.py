from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import api_router
from app.core.cache import cache_service
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    DomainException,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    IdempotencyConflictError,
    InvalidStateTransitionError,
    PermissionDeniedError,
)
from app.core.middleware import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize cache connection pool on startup
    await cache_service.get_client()
    yield
    # Graceful shutdown
    await cache_service.close()


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. Security Headers Middleware (OWASP, HSTS, CSP with docs exemption)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Domain Exception Handlers (Mapping Domain Logic to HTTP Status Codes)
    @app.exception_handler(EntityNotFoundError)
    async def not_found_handler(request: Request, exc: EntityNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "Not Found", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(EntityAlreadyExistsError)
    async def already_exists_handler(request: Request, exc: EntityAlreadyExistsError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "Conflict", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Forbidden", "message": exc.message},
        )

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Unauthorized", "message": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_handler(request: Request, exc: IdempotencyConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "Idempotency Conflict", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(InvalidStateTransitionError)
    async def state_transition_handler(request: Request, exc: InvalidStateTransitionError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Invalid State Transition", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(DomainException)
    async def generic_domain_handler(request: Request, exc: DomainException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Bad Request", "message": exc.message, "details": exc.details},
        )

    # 4. Include API Routers
    app.include_router(api_router)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs_url": "/docs",
            "health_url": "/health",
        }

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_application()
