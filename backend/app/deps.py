from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.afsc import AfscEngine, get_afsc_engine
from app.db.session import get_session
from app.services.agent_service import AgentService
from app.services.import_service import ImportService
from app.services.member_service import MemberService


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def get_afsc() -> AfscEngine:
    return get_afsc_engine()


def get_import_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    afsc: AfscEngine = Depends(get_afsc),
) -> ImportService:
    return ImportService(db, afsc, max_upload_bytes=settings.max_upload_bytes)


def get_member_service(
    db: Session = Depends(get_db),
    afsc: AfscEngine = Depends(get_afsc),
) -> MemberService:
    return MemberService(db, afsc)


def get_agent_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    afsc: AfscEngine = Depends(get_afsc),
) -> AgentService:
    return AgentService(db, settings=settings, afsc_engine=afsc)
