from fastapi import APIRouter

from . import afsc, chat, health, members, roster

router = APIRouter()
router.include_router(health.router)
router.include_router(roster.router)
router.include_router(members.router)
router.include_router(afsc.router)
router.include_router(chat.router)
