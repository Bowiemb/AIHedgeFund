"""API v1 main router."""

from fastapi import APIRouter

from apps.api.v1.endpoints import (
    companies,
    filings,
    statements,
    holdings,
    signals,
    usage,
    auth,
)

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(filings.router, prefix="/filings", tags=["filings"])
api_router.include_router(statements.router, prefix="/statements", tags=["statements"])
api_router.include_router(holdings.router, prefix="/holdings/13f", tags=["holdings-13f"])
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
