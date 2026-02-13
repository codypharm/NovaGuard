"""Non-blocking audit logger for clinical interactions."""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from nova_guard.models.audit import AuditLog

logger = logging.getLogger(__name__)

# Max chars to store for query/response — keeps DB lean
_MAX_QUERY_LEN = 500
_MAX_RESPONSE_LEN = 500


async def log_interaction(
    db: AsyncSession,
    *,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: str = "clinical_interaction",
    intent: Optional[str] = None,
    query: Optional[str] = None,
    response_summary: Optional[str] = None,
    verdict_status: Optional[str] = None,
    flag_count: int = 0,
) -> None:
    """
    Persist an audit record. Non-blocking — swallows errors
    so a logging failure never breaks the user flow.
    """
    try:
        record = AuditLog(
            session_id=session_id,
            user_id=user_id,
            action=action,
            intent=intent,
            query=(query[:_MAX_QUERY_LEN] if query else None),
            response_summary=(response_summary[:_MAX_RESPONSE_LEN] if response_summary else None),
            verdict_status=verdict_status,
            flag_count=flag_count,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        await db.commit()
        logger.debug("Audit record saved: session=%s action=%s", session_id, action)
    except Exception as e:
        logger.warning("Audit logging failed (non-fatal): %s", e)
        await db.rollback()
