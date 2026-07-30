from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.afsc import AfscEngine, get_afsc_engine
from app.afsc.matcher import afsc_pattern_to_sql_like
from app.db.repositories.members import MemberRepository
from app.enums import PersonnelType
from app.exceptions import AfscResolutionError, AfscValidationError
from app.schemas import MemberOut, TeamCheckOut, TeamRequirementIn, TeamRequirementResultOut


@dataclass(frozen=True)
class _TeamPool:
    afsc: str
    personnel_type: PersonnelType | None
    needed: int
    member_ids: frozenset[uuid.UUID]
    labels: tuple[str, ...]
    error: str | None = None


class MemberService:
    def __init__(
        self,
        session: Session,
        afsc_engine: AfscEngine | None = None,
    ) -> None:
        self._members = MemberRepository(session)
        self._afsc = afsc_engine or get_afsc_engine()

    def list_members(
        self,
        *,
        name: str | None = None,
        dodid: str | None = None,
        afsc_pattern: str | None = None,
        personnel_type: PersonnelType | None = None,
        limit: int | None = 25,
        offset: int = 0,
    ) -> list[MemberOut]:
        afsc_like = afsc_pattern_to_sql_like(afsc_pattern) if afsc_pattern else None
        records = self._members.list_active(
            name_query=name,
            dodid=dodid,
            personnel_type=personnel_type,
            afsc_like=afsc_like,
            limit=limit,
            offset=offset,
        )
        return [self._to_out(r) for r in records]

    def count_members(
        self,
        *,
        name: str | None = None,
        dodid: str | None = None,
        afsc_pattern: str | None = None,
        personnel_type: PersonnelType | None = None,
    ) -> int:
        afsc_like = afsc_pattern_to_sql_like(afsc_pattern) if afsc_pattern else None
        return self._members.count_active(
            name_query=name,
            dodid=dodid,
            personnel_type=personnel_type,
            afsc_like=afsc_like,
        )

    def check_team(self, requirements: list[TeamRequirementIn]) -> TeamCheckOut:
        pools: list[_TeamPool] = []
        for req in requirements:
            try:
                afsc_like = afsc_pattern_to_sql_like(req.afsc)
                member_ids = frozenset(
                    self._members.list_active_ids(
                        personnel_type=req.personnel_type,
                        afsc_like=afsc_like,
                    )
                )
                labels = tuple(self._afsc.search_labels(req.afsc))
                pools.append(
                    _TeamPool(
                        afsc=req.afsc,
                        personnel_type=req.personnel_type,
                        needed=req.needed,
                        member_ids=member_ids,
                        labels=labels,
                    )
                )
            except (AfscValidationError, AfscResolutionError) as exc:
                pools.append(
                    _TeamPool(
                        afsc=req.afsc,
                        personnel_type=req.personnel_type,
                        needed=req.needed,
                        member_ids=frozenset(),
                        labels=(),
                        error=str(exc),
                    )
                )

        assigned = self._assign_distinct([(p.needed, p.member_ids) for p in pools])
        results: list[TeamRequirementResultOut] = []
        for pool, got in zip(pools, assigned, strict=True):
            shortfall = max(0, pool.needed - got)
            results.append(
                TeamRequirementResultOut(
                    afsc=pool.afsc,
                    personnel_type=pool.personnel_type,
                    needed=pool.needed,
                    eligible=len(pool.member_ids),
                    assigned=got,
                    shortfall=shortfall,
                    can_fill=shortfall == 0 and pool.error is None,
                    labels=list(pool.labels),
                    error=pool.error,
                )
            )
        return TeamCheckOut(
            can_form=all(r.can_fill for r in results),
            results=results,
        )

    @staticmethod
    def _assign_distinct(
        pools: list[tuple[int, frozenset[uuid.UUID]]],
    ) -> list[int]:
        if not pools:
            return []

        source = "s"
        sink = "t"
        capacity: dict[str, dict[str, int]] = defaultdict(dict)

        member_keys: dict[uuid.UUID, str] = {}
        for i, (needed, ids) in enumerate(pools):
            req = f"r{i}"
            capacity[source][req] = needed
            for member_id in ids:
                key = member_keys.setdefault(member_id, f"m{len(member_keys)}")
                capacity[req][key] = 1
                capacity[key][sink] = 1

        def bfs(parent: dict[str, str | None]) -> int:
            parent.clear()
            parent[source] = None
            queue: deque[tuple[str, int]] = deque([(source, 10**9)])
            while queue:
                node, flow = queue.popleft()
                for nxt, cap in capacity[node].items():
                    if nxt in parent or cap <= 0:
                        continue
                    parent[nxt] = node
                    pumped = min(flow, cap)
                    if nxt == sink:
                        return pumped
                    queue.append((nxt, pumped))
            return 0

        parent: dict[str, str | None] = {}
        while True:
            pumped = bfs(parent)
            if pumped == 0:
                break
            node = sink
            while node != source:
                prev = parent[node]
                assert prev is not None
                capacity[prev][node] -= pumped
                capacity[node][prev] = capacity[node].get(prev, 0) + pumped
                node = prev

        return [
            pools[i][0] - capacity[source].get(f"r{i}", 0)
            for i in range(len(pools))
        ]

    def _to_out(self, record) -> MemberOut:
        label = family = level = specialization = None
        labels: list[str] = []
        try:
            resolved = self._afsc.resolve(record.normalized_afsc)
            label = resolved.full_label
            labels = list(resolved.breakdown)
            family = resolved.family
            level = resolved.level
            specialization = resolved.specialization
        except (AfscValidationError, AfscResolutionError):
            pass

        return MemberOut(
            id=record.id,
            dodid=record.dodid,
            display_name=record.display_name,
            rank=record.rank,
            personnel_type=record.personnel_type,
            afsc=record.afsc,
            normalized_afsc=record.normalized_afsc,
            afsc_label=label,
            afsc_labels=labels,
            afsc_family=family,
            afsc_level=level,
            afsc_specialization=specialization,
            created_at=record.created_at,
        )
