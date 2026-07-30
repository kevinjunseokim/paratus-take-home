from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.afsc import AfscEngine, get_afsc_engine
from app.config import Settings, get_settings
from app.exceptions import DomainError
from app.services.agent_prompts import SYSTEM_PROMPT
from app.services.agent_tools import TOOL_DEFINITIONS, AgentToolExecutor
from app.services.member_service import MemberService


class AgentService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        afsc_engine: AfscEngine | None = None,
        openai_client: OpenAI | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._afsc = afsc_engine or get_afsc_engine()
        self._members = MemberService(session, self._afsc)
        self._tools = AgentToolExecutor(self._members, self._afsc)
        self._client = openai_client

    def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        if not self._settings.openai_api_key and self._client is None:
            raise DomainError("OPENAI_API_KEY is not configured")

        client = self._client or OpenAI(api_key=self._settings.openai_api_key)
        working: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *messages,
        ]
        traces: list[dict[str, Any]] = []

        for _ in range(5):
            response = client.chat.completions.create(
                model=self._settings.openai_model,
                messages=working,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            choice = response.choices[0].message
            tool_calls = choice.tool_calls or []

            if not tool_calls:
                return {"reply": choice.content or "", "tool_traces": traces}

            working.append(
                {
                    "role": "assistant",
                    "content": choice.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                raw_args = tc.function.arguments or "{}"
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    arguments = {}
                    result = {"ok": False, "error": "Tool arguments were not valid JSON"}
                else:
                    if not isinstance(arguments, dict):
                        result = {"ok": False, "error": "Tool arguments must be an object"}
                    else:
                        result = self._tools.execute(tc.function.name, arguments)

                traces.append(
                    {"tool": tc.function.name, "arguments": arguments, "result": result}
                )
                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

        return {
            "reply": "I could not complete the request within the tool-call limit.",
            "tool_traces": traces,
        }
