"""
app/agents/conversation_agent.py — ReAct-style AI spare parts consultant agent.

Loop per turn:
  1. Build prompt (system + tool descriptions + history + user message)
  2. Call LLM
  3. Parse ReAct JSON output: {thought, action, args} or {thought, action:"respond", text}
  4. If action is a tool name → execute tool, append observation, repeat
  5. If action == "respond" → return text to user
  6. Max MAX_ITERATIONS iterations per turn; escalate if exceeded

Safety: escalation is forced in code when confidence is below threshold or
turn_count exceeds the limit — independent of what the LLM decides.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config.settings import settings
from app.core.schemas import ConversationContext, ReActOutput, ToolCallRecord
from app.llm.client import llm_client
from app.llm.parser import extract_json
from app.prompts.conversation import ConversationPrompt
from app.tools.registry import tool_registry

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5
_prompt = ConversationPrompt()


@dataclass
class TurnResult:
    response:   str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    escalated:  bool = False
    confidence: float | None = None


class ConversationAgent(BaseAgent):
    name        = "conversation_agent"
    description = "ReAct tool-use agent for spare parts identification and consultation"

    def __init__(self, session: AsyncSession, context: ConversationContext):
        self._session = session
        self._context = context

    async def run(self, input: dict) -> TurnResult:
        """
        input keys:
          history      list[dict]   — prior messages [{role, text}, ...]
          user_message str          — current user turn
        """
        history      = input["history"]
        user_message = input["user_message"]
        tool_calls   = []

        # Accumulate tool observations for this turn in a local history copy
        turn_history = list(history)

        for iteration in range(MAX_ITERATIONS):
            messages = _prompt.build(history=turn_history, user_message=user_message)

            try:
                raw = await llm_client.chat(messages, temperature=settings.llm_temperature)
            except Exception as e:
                logger.exception("LLM call failed on iteration %d", iteration)
                return self._escalate(tool_calls, reason=f"LLM недоступен: {e}")

            # Parse ReAct JSON
            try:
                data     = extract_json(raw)
                react    = ReActOutput.model_validate(data)
            except Exception:
                logger.warning("Failed to parse ReAct output: %s", raw[:300])
                # Treat unparseable output as a final text response
                return TurnResult(response=raw.strip(), tool_calls=tool_calls)

            logger.debug("[iter %d] thought=%s action=%s", iteration, react.thought[:80], react.action)

            if react.action == "respond":
                text = (react.text or "").strip()
                if not text:
                    text = "Пожалуйста, уточните ваш вопрос."
                return TurnResult(
                    response=text,
                    tool_calls=tool_calls,
                    escalated=self._context.escalated,
                    confidence=self._context.last_confidence,
                )

            # Execute tool
            tool_result = await tool_registry.execute(
                react.action, react.args, self._session, self._context
            )

            record = ToolCallRecord(tool=react.action, args=react.args, result=tool_result)
            tool_calls.append(record)

            # Append observation to turn history so next iteration sees it
            obs_text = (
                f"[Инструмент: {react.action}]\n"
                f"Мысль: {react.thought}\n"
                f"Результат: {tool_result}"
            )
            turn_history.append({"role": "assistant", "text": obs_text})

            # Check if escalation was triggered by the tool
            if self._context.escalated:
                escalation_msg = (
                    tool_result.get("message")
                    or "Ваш запрос передан менеджеру. Специалист свяжется с вами."
                )
                return TurnResult(
                    response=escalation_msg,
                    tool_calls=tool_calls,
                    escalated=True,
                )

        # Max iterations reached — escalate
        return self._escalate(tool_calls, reason="Превышен лимит шагов рассуждения")

    def _escalate(self, tool_calls: list[ToolCallRecord], reason: str) -> TurnResult:
        self._context.escalated         = True
        self._context.escalation_reason = reason
        return TurnResult(
            response=(
                "К сожалению, мне не удалось найти точный ответ на ваш вопрос. "
                "Ваш запрос передан менеджеру — он свяжется с вами в ближайшее время."
            ),
            tool_calls=tool_calls,
            escalated=True,
        )
