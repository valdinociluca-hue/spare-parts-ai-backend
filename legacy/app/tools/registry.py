"""
app/tools/registry.py — Tool registry and BaseTool interface.

Each tool has:
  - name: str           (used in ReAct action field)
  - description: str    (injected into system prompt)
  - parameters: dict    (JSON Schema — also injected into prompt)
  - execute(args, session, context) -> dict

The LLM never calls tools directly. The ConversationAgent parses
the ReAct JSON output and dispatches to the registry.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict   # JSON Schema object

    @abstractmethod
    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        ...

    def to_prompt_block(self) -> str:
        """Renders this tool as a block for injection into the system prompt."""
        import json
        return (
            f"Tool: {self.name}\n"
            f"Description: {self.description}\n"
            f"Parameters: {json.dumps(self.parameters, ensure_ascii=False)}"
        )


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def prompt_description(self) -> str:
        """Returns all tools formatted for system prompt injection."""
        blocks = [t.to_prompt_block() for t in self._tools.values()]
        return "\n\n".join(blocks)

    async def execute(
        self,
        name: str,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await tool.execute(args, session, context)
        except Exception as e:
            logger.exception("Tool %s failed: %s", name, e)
            return {"error": str(e)}


# Singleton registry — tools are registered at import time
tool_registry = ToolRegistry()
