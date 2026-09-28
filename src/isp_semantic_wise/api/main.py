"""
Main API Router - FastAPI application with all routes
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from isp_semantic_wise.config import get_settings, Settings
from isp_semantic_wise.api.routes import glossary, nl2sql, debugger, narrator, impact, lineage, health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()
    logger.info("starting_application", version=settings.version, environment=settings.environment)

    # Initialize connections
    # await init_vector_db()
    # await init_graph_db()
    # await init_relational_db()

    logger.info("application_started")
    yield

    # Cleanup
    logger.info("shutting_down")
    # await close_connections()


def create_app(settings: Settings = None) -> FastAPI:
    """Create FastAPI application"""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="ISPSemanticWise API",
        description="SME Knowledge Builder for Capital Markets Post-Trade Management",
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500},
        )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(glossary.router, prefix="/api/v1/glossary", tags=["Glossary"])
    app.include_router(nl2sql.router, prefix="/api/v1/nl2sql", tags=["NL2SQL"])
    app.include_router(debugger.router, prefix="/api/v1/debugger", tags=["Debugger"])
    app.include_router(narrator.router, prefix="/api/v1/narrator", tags=["Narrator"])
    app.include_router(impact.router, prefix="/api/v1/impact", tags=["Impact"])
    app.include_router(lineage.router, prefix="/api/v1/lineage", tags=["Lineage"])

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "isp_semantic_wise.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.api.workers if not settings.debug else 1,
    )