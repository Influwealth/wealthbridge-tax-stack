"""
Tenant context middleware.

Reads X-Tenant-ID header from incoming requests and injects the tenant
into request.state so downstream handlers can scope queries accordingly.

In a real deployment, tenant resolution would happen after JWT auth;
here we trust the header for simplicity (production would verify the
user's membership in the claimed tenant).

Header: X-Tenant-ID: <tenant_id: int>
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from tax_capsule.utils.logger import get_logger

logger = get_logger("TenantMiddleware")

TENANT_HEADER = "X-Tenant-ID"


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id_str = request.headers.get(TENANT_HEADER)
        tenant_id = None

        if tenant_id_str:
            try:
                tenant_id = int(tenant_id_str)
                logger.debug(f"Tenant context: {tenant_id} on {request.url.path}")
            except ValueError:
                logger.warning(f"Invalid X-Tenant-ID header: {tenant_id_str!r}")

        request.state.tenant_id = tenant_id
        return await call_next(request)


def get_tenant_id(request: Request) -> int | None:
    """FastAPI dependency: extract tenant_id from request state."""
    return getattr(request.state, "tenant_id", None)
