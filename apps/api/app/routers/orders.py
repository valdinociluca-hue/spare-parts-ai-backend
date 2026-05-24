from fastapi import APIRouter

from app.deps import CurrentTenant, Tenant

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/draft")
async def draft_order(tenant: Tenant = CurrentTenant) -> dict[str, str]:
    """Module 3 entry point (placeholder)."""
    _ = tenant
    return {"status": "draft", "items": "[]"}
