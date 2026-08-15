"""LLM client with function-calling loop.

Wraps the OpenAI SDK with:
1. Tool (function calling) support
2. Structured telemetry logging to PostgreSQL
3. Automatic provider endpoint detection (OpenAI, Gemini, Groq, Local)
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
    """Create an async OpenAI-compatible client with auto-provider detection."""
    settings = get_settings()
    api_key = settings.openai_api_key or ""
    base_url = settings.openai_base_url

    # Auto-detect Google Gemini if model is gemini or API key starts with AIza
    if not base_url:
        if settings.openai_model.startswith("gemini") or api_key.startswith("AIza"):
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            logger.info("Auto-configured Google Gemini OpenAI compatibility endpoint: %s", base_url)

    kwargs: dict = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

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
    """Execute an LLM call with iterative tool calling."""
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

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        call_cost = calculate_cost(model, prompt_tokens, completion_tokens)
        total_cost += call_cost

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
        messages.append(message.model_dump())

        if not message.tool_calls:
            return (
                message.content or "",
                messages,
                total_cost,
                total_latency,
            )

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

            await _log_tool_call(
                db=db,
                run_id=run_id,
                state=state,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=tool_result,
                latency_ms=tool_latency,
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    return (
        "Maximum tool-calling rounds reached.",
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
