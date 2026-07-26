import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports import build_daily_report
from shared.config import settings
from shared.database import get_session

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("netxia.analytics")

app = FastAPI(title="Netxia Analytics Service", version="1.0.0")


@app.get("/v1/reports/daily/{tenant_id}")
async def daily_report(tenant_id: UUID, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    report_text = await build_daily_report(session, tenant_id, since)
    return {"report": report_text}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "analytics"}
