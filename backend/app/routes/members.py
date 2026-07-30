from fastapi import APIRouter, Depends, Query

from app.deps import get_member_service
from app.enums import PersonnelType
from app.schemas import MembersPageOut, TeamCheckIn, TeamCheckOut
from app.services.member_service import MemberService

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("", response_model=MembersPageOut)
def list_members(
    name: str | None = Query(default=None),
    dodid: str | None = Query(default=None),
    afsc: str | None = Query(default=None),
    personnel_type: PersonnelType | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: MemberService = Depends(get_member_service),
) -> MembersPageOut:
    members = service.list_members(
        name=name,
        dodid=dodid,
        afsc_pattern=afsc,
        personnel_type=personnel_type,
        limit=limit,
        offset=offset,
    )
    total = service.count_members(
        name=name,
        dodid=dodid,
        afsc_pattern=afsc,
        personnel_type=personnel_type,
    )
    return MembersPageOut(members=members, total=total, limit=limit, offset=offset)


@router.post("/team-check", response_model=TeamCheckOut)
def check_team(
    body: TeamCheckIn,
    service: MemberService = Depends(get_member_service),
) -> TeamCheckOut:
    return service.check_team(body.requirements)
