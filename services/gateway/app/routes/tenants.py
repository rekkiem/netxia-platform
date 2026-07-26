"""
Endpoints de administración de tenants: alta de nuevos clientes de la
plataforma (empresas), cada uno con su propio número SIP y/o instancia
WhatsApp asociada.
"""
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_session

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])


class TenantCreateRequest(BaseModel):
    name: str
    subdomain: str
    config: dict = {}


class TenantResponse(BaseModel):
    id: UUID
    name: str
    subdomain: str


@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(
    request: TenantCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> TenantResponse:
    tenant_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO tenants (id, name, subdomain, config, created_at)
            VALUES (:id, :name, :subdomain, :config, now())
            """
        ),
        {
            "id": str(tenant_id),
            "name": request.name,
            "subdomain": request.subdomain,
            "config": str(request.config),
        },
    )
    await session.commit()
    return TenantResponse(id=tenant_id, name=request.name, subdomain=request.subdomain)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: UUID, session: AsyncSession = Depends(get_session)) -> TenantResponse:
    result = await session.execute(
        text("SELECT id, name, subdomain FROM tenants WHERE id = :id"),
        {"id": str(tenant_id)},
    )
    row = result.fetchone()
    return TenantResponse(id=row.id, name=row.name, subdomain=row.subdomain)
