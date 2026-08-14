"""LLM client with function-calling loop.

Wraps the OpenAI API with:
1. Tool (function calling) support — iterates until the LLM stops calling tools
2. Structured logging — every call logs tokens, cost, and latency
3. Conversation history management — accumulates messages across iterations

Design decision: We use the OpenAI SDK directly (not LangChain) for full
control over the function-calling loop. This makes the behavior transparent
and avoids framework-imposed abstractions that obscure what the LLM sees.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from app.agent.tools import TOOL_DEFINITIONS, execute_tool
from app.core.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.sandbox.docker_sandbox import DockerSandbox

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (GPT-4o, GPT-4.1, and Google Gemini free tier)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gemini-2.5-flash": {"input": 0.00, "output": 0.00},
    "gemini-2.0-flash": {"input": 0.00, "output": 0.00},
    "gemini-1.5-flash": {"input": 0.00, "output": 0.00},
}


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate the cost of an LLM call in USD."""
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


async def create_llm_client() -> AsyncOpenAI:
    """Create an async OpenAI-compatible client.

    Supports OpenAI, Google Gemini (via OpenAI compatibility endpoint),
    Groq, Ollama, and other providers.
    """
    settings = get_settings()
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return AsyncOpenAI(**kwargs)


async def llm_call_with_tools(
    messages: list[dict],
    run_id: uuid.UUID,
    state: str,
    sandbox: DockerSandbox | None,
    db: AsyncSession,
    model: str | None = None,
    max_tool_rounds: int = 15,
) -> tuple[str, list[dict], float, float]:
    """Execute an LLM call with iterative tool calling.

    The LLM may call tools multiple times. We loop until:
    1. The LLM returns a text response (no tool calls), or
    2. We hit max_tool_rounds (safety limit).

    Args:
        messages: Conversation history (modified in place).
        run_id: Current run ID for logging.
        state: Current FSM state for logging.
        sandbox: Docker sandbox for tool execution (None for dry runs).
        db: Database session for logging.
        model: Override model name.
        max_tool_rounds: Maximum number of tool-calling rounds.

    Returns:
        (response_text, updated_messages, total_cost, total_latency_ms)
    """
    settings = get_settings()
    model = model or settings.openai_model
    client = await create_llm_client()

    total_cost = 0.0
    total_latency = 0.0

    for round_num in range(max_tool_rounds):
        start_time = time.perf_counter()

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        latency_ms = (time.perf_counter() - start_time) * 1000
        total_latency += latency_ms

        # Extract usage info
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        call_cost = calculate_cost(model, prompt_tokens, completion_tokens)
        total_cost += call_cost

        # Log the LLM call
        await _log_llm_call(
            db=db,
            run_id=run_id,
            state=state,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=call_cost,
        )

        choice = response.choices[0]
        message = choice.message

        # Add assistant message to conversation
        messages.append(message.model_dump())

        # If no tool calls, we're done — return the text response
        if not message.tool_calls:
            return (
                message.content or "",
                messages,
                total_cost,
                total_latency,
            )

        # Process tool calls
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            logger.info(
                "Tool call",
                extra={
                    "run_id": str(run_id),
                    "tool": tool_name,
                    "args": tool_args,
                    "round": round_num,
                },
            )

            # Execute the tool
            tool_start = time.perf_counter()
            try:
                if sandbox is None:
                    tool_result = f"Sandbox not available — tool '{tool_name}' skipped"
                else:
                    tool_result = await execute_tool(tool_name, tool_args, sandbox)
            except Exception as e:
                tool_result = f"Tool error: {e}"
                logger.exception("Tool execution failed", extra={"tool": tool_name})

            tool_latency = (time.perf_counter() - tool_start) * 1000

            # Log the tool call
            await _log_tool_call(
                db=db,
                run_id=run_id,
                state=state,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result,
                latency_ms=tool_latency,
            )

            # Add tool result to conversation
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    # Safety: hit max rounds
    logger.warning(
        "Max tool rounds reached",
        extra={"run_id": str(run_id), "max_rounds": max_tool_rounds},
    )
    return (
        "Maximum tool-calling rounds reached. Please provide a response.",
        messages,
        total_cost,
        total_latency,
    )


async def _log_llm_call(
    db: AsyncSession,
    run_id: uuid.UUID,
    state: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    cost_usd: float,
) -> None:
    """Log an LLM call to the database."""
    from app.models.log_entry import LogEntry

    entry = LogEntry(
        run_id=run_id,
        entry_type="llm_call",
        state=state,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )
    db.add(entry)
    await db.flush()


async def _log_tool_call(
    db: AsyncSession,
    run_id: uuid.UUID,
    state: str,
    tool_name: str,
    tool_args: dict,
    tool_result: str,
    latency_ms: float,
) -> None:
    """Log a tool call to the database."""
    from app.models.log_entry import LogEntry

    entry = LogEntry(
        run_id=run_id,
        entry_type="tool_call",
        state=state,
        tool_name=tool_name,
        tool_args=tool_args,
        tool_result_preview=tool_result[:500] if tool_result else None,
        latency_ms=latency_ms,
    )
    db.add(entry)
    await db.flush()
