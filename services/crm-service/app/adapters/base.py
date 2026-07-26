"""
Interfaz común que deben implementar todos los adaptadores CRM
(EspoCRM, SuiteCRM, Odoo). Esto es lo que permite "Desacoplamiento total":
el conversation-engine y crm-service nunca hablan directamente con la API
particular de un CRM, solo con esta interfaz.
"""
from abc import ABC, abstractmethod
from typing import Any


class CRMAdapter(ABC):
    @abstractmethod
    async def upsert_contact(self, tenant_id: str, phone_number: str, name: str | None) -> str:
        """Crea o actualiza un contacto. Retorna el ID del contacto en el CRM."""
        raise NotImplementedError

    @abstractmethod
    async def log_conversation(self, tenant_id: str, contact_id: str, summary: str, channel: str) -> None:
        """Registra un resumen de la conversación como actividad/nota en el CRM."""
        raise NotImplementedError

    @abstractmethod
    async def is_healthy(self) -> bool:
        raise NotImplementedError


class CRMAdapterError(Exception):
    """Error genérico de comunicación con un CRM externo."""


def get_adapter(crm_type: str) -> CRMAdapter:
    """Factory que resuelve el adaptador concreto según configuración del
    tenant, sin acoplar al llamador a las clases concretas."""
    from app.adapters.espocrm import EspoCRMAdapter
    from app.adapters.odoo import OdooAdapter
    from app.adapters.suitecrm import SuiteCRMAdapter

    adapters: dict[str, type[CRMAdapter]] = {
        "espocrm": EspoCRMAdapter,
        "suitecrm": SuiteCRMAdapter,
        "odoo": OdooAdapter,
    }
    adapter_cls = adapters.get(crm_type)
    if adapter_cls is None:
        raise CRMAdapterError(f"CRM no soportado: {crm_type}")
    return adapter_cls()
