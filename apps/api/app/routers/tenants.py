from fastapi import APIRouter

from app.deps import CurrentTenant, Tenant
from app.schemas import TenantOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantOut)
async def get_my_tenant(tenant: Tenant = CurrentTenant) -> Tenant:
    return tenant
