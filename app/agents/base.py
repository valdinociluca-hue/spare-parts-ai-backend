"""
app/agents/base.py — Abstract base class for all agents.

An "agent" in this system is a unit of autonomous reasoning that:
  - Receives a structured input (e.g. a customer request)
  - Uses one or more tools (LLM calls, RAG lookups, DB queries, API calls)
  - Produces a structured output (classification, draft reply, extracted data)
  - Optionally calls other agents (multi-agent coordination)

All concrete agents inherit from BaseAgent and implement `run()`.

This abstraction lets the orchestrator treat agents uniformly:
  result = await agent.run(input)

Future evolution:
  - Add tool registration (agent.register_tool(...))
  - Add memory/context window management
  - Add streaming support (agent.stream(input))
  - Add observability hooks (on_tool_call, on_llm_response)
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base for all agent implementations."""

    name: str = "base_agent"
    description: str = ""

    @abstractmethod
    async def run(self, input: Any) -> Any:
        """
        Execute the agent logic.

        Args:
            input: Agent-specific input (Pydantic model recommended)

        Returns:
            Agent-specific output (Pydantic model recommended)
        """
        ...
